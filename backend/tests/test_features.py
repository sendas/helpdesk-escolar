"""Ratings, @mentions, quick replies, monthly report, planned maintenance and the mailbox."""
from datetime import date, timedelta

import pytest

from tests.test_notifications import outbox  # noqa: F401  (fixture)
from tests.test_smoke import _new_ticket

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_requester_rates_a_finished_ticket(client, people, api):
    tid = await _new_ticket(client, people, api, "Avaliar")
    r = await client.put(f"{api}/tickets/{tid}/rating", headers=people["prof"]["h"], json={"stars": 5})
    assert r.status_code == 400  # not finished yet
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "resolved"})
    assert (await client.put(f"{api}/tickets/{tid}/rating", headers=people["tec"]["h"], json={"stars": 5})).status_code == 404
    r = await client.put(f"{api}/tickets/{tid}/rating", headers=people["prof"]["h"], json={"stars": 4, "comment": "Rápido!"})
    assert r.status_code == 200 and r.json()["stars"] == 4
    t = (await client.get(f"{api}/tickets/{tid}", headers=people["tec"]["h"])).json()
    assert t["rating"]["stars"] == 4
    stats = (await client.get(f"{api}/admin/stats", headers=people["adm"]["h"])).json()["ratings"]
    assert stats["count"] >= 1 and stats["recent_comments"][0]["comment"] == "Rápido!"


async def test_mentions_notify_only_who_may_read(client, people, api, outbox):  # noqa: F811
    tid = await _new_ticket(client, people, api, "Menções")
    outbox.clear()
    # Internal note: the docente mentioned is ignored, the technician is told
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={
        "body": "@Rui @Maria vejam isto", "is_internal": True, "mention_ids": [people["tec2"]["id"], people["prof"]["id"]],
    })
    assert r.status_code == 201
    assert r.json()["mention_ids"] == str(people["tec2"]["id"])
    mentioned = [to for to, ev, _ in outbox if ev == "mentioned"]
    assert mentioned == ["tec2@escola.pt"]


async def test_quick_replies_are_editable(client, people, api):
    r = await client.get(f"{api}/settings/quick-replies", headers=people["tec"]["h"])
    assert r.status_code == 200 and len(r.json()["replies"]) == 3
    r = await client.put(f"{api}/settings/quick-replies", headers=people["adm"]["h"], json={"replies": [
        {"label": "Visita agendada", "body": "Vamos passar pela sala amanhã.", "status": "in_progress"},
    ]})
    assert r.status_code == 200
    assert (await client.get(f"{api}/settings/quick-replies", headers=people["tec"]["h"])).json()["replies"][0]["label"] == "Visita agendada"
    assert (await client.put(f"{api}/settings/quick-replies", headers=people["tec"]["h"], json={"replies": []})).status_code == 403
    public = (await client.get(f"{api}/settings/public")).json()
    assert "quick_replies" not in public and "suggestion_emails" not in public


async def test_monthly_report(client, people, api):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    month = f"{now.year:04d}-{now.month:02d}"
    r = await client.get(f"{api}/admin/report", params={"month": month}, headers=people["adm"]["h"])
    assert r.status_code == 200 and r.json()["created"] >= 1
    html = (await client.get(f"{api}/admin/report/html", params={"month": month}, headers=people["adm"]["h"])).text
    assert "Relatório de" in html and "Pedidos por escola" in html
    assert (await client.get(f"{api}/admin/report", headers=people["prof"]["h"])).status_code == 403


async def test_planned_maintenance_creates_tickets(client, people, api):
    cats = (await client.get(f"{api}/categories", headers=people["adm"]["h"])).json()
    schools = (await client.get(f"{api}/schools", headers=people["adm"]["h"])).json()
    r = await client.post(f"{api}/planning", headers=people["tec"]["h"], json={
        "title": "Verificar projetores", "description": "Todas as salas.", "category_id": cats[0]["id"], "school_id": schools[0]["id"],
        "assignee_id": people["tec2"]["id"], "frequency": "monthly", "next_run": (date.today() - timedelta(days=1)).isoformat(),
    })
    assert r.status_code == 201, r.text
    plan_id = r.json()["id"]
    from app.database import AsyncSessionLocal
    from app.services import planning_service
    async with AsyncSessionLocal() as db:
        assert await planning_service.run_due(db) == 1
    plans = (await client.get(f"{api}/planning", headers=people["tec"]["h"])).json()["items"]
    plan = next(p for p in plans if p["id"] == plan_id)
    assert plan["last_ticket_id"] and date.fromisoformat(plan["next_run"]) > date.today()
    t = (await client.get(f"{api}/tickets/{plan['last_ticket_id']}", headers=people["tec2"]["h"])).json()
    assert t["title"] == "Verificar projetores" and any(a["id"] == people["tec2"]["id"] for a in t["assignees"])
    assert (await client.post(f"{api}/planning", headers=people["prof"]["h"], json={})).status_code in (403, 422)


async def test_mailbox_with_a_fake_connection(client, people, api, monkeypatch):
    from app.services import mailbox as mb

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 40

    class Fake:
        name = "graph"
        can_archive = True
        read = {}

        async def list(self, page):
            return [mb.MailSummary("m1", "Impressora encravada", "Maria", "prof@escola.pt", "2026-09-29T10:00:00Z", False,
                                   "A impressora da sala 3...", True, "<m1@x>")], False

        async def get(self, mid, with_content=False):
            return mb.MailMessage("m1", "Impressora encravada", "Maria", "prof@escola.pt", "2026-09-29T10:00:00Z", False,
                                  "A impressora...", True, "<m1@x>", body="A impressora da sala 3 está encravada.",
                                  attachments=[mb.MailAttachment("foto.png", "image/png", len(png), png if with_content else None),
                                               mb.MailAttachment("virus.exe", "application/octet-stream", 3, b"MZx" if with_content else None)])

        async def set_read(self, mid, read):
            Fake.read[mid] = read

        async def archive(self, mid):
            pass

    monkeypatch.setattr(mb, "get_provider", lambda: Fake())
    assert (await client.get(f"{api}/mailbox", headers=people["prof"]["h"])).status_code == 403
    listing = (await client.get(f"{api}/mailbox", headers=people["tec"]["h"])).json()
    assert listing["configured"] and listing["items"][0]["sender_known"] and listing["items"][0]["ticket_id"] is None
    detail = (await client.get(f"{api}/mailbox/message", params={"id": "m1"}, headers=people["tec"]["h"])).json()
    assert detail["sender"]["id"] == people["prof"]["id"] and len(detail["attachments"]) == 2
    cats = (await client.get(f"{api}/categories", headers=people["adm"]["h"])).json()
    schools = (await client.get(f"{api}/schools", headers=people["adm"]["h"])).json()
    r = await client.post(f"{api}/mailbox/ticket", headers=people["tec"]["h"], json={"id": "m1", "category_id": cats[0]["id"], "school_id": schools[0]["id"]})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["requester_found"] and out["attachments"] == 1 and out["skipped"] == ["virus.exe"]
    t = (await client.get(f"{api}/tickets/{out['ticket_id']}", headers=people["prof"]["h"])).json()
    assert t["creator"]["id"] == people["prof"]["id"] and t["title"] == "Impressora encravada"
    assert Fake.read.get("m1") is True
    listing = (await client.get(f"{api}/mailbox", headers=people["tec"]["h"])).json()
    assert listing["items"][0]["ticket_id"] == out["ticket_id"]
    # The same email cannot be imported twice
    r = await client.post(f"{api}/mailbox/attach", headers=people["tec"]["h"], json={"id": "m1", "ticket_id": out["ticket_id"]})
    assert r.status_code == 409


async def test_no_access_form_for_students(client, api, monkeypatch):
    from app.api.v1.settings import _update_settings
    from app.config import settings
    from app.services import email_service
    sent = []

    async def fake(to, data):
        sent.append(data)

    monkeypatch.setattr(settings, "mail_server", "smtp.test")
    monkeypatch.setattr(email_service, "send_no_access_contact", fake)
    _update_settings({"no_access_contact_email": "apoio@escola.pt"})
    base = {"profile": "aluno", "name": "João Aluno", "message": "Não consigo entrar", "school": "EB Eça"}
    r = await client.post(f"{api}/auth/no-access-contact", json={**base, "student_number": "12345", "year": "8.º", "class_name": "b"})
    assert r.status_code == 400 and "cartão" in r.json()["detail"]
    r = await client.post(f"{api}/auth/no-access-contact", json={**base, "student_number": "A12345", "year": "8.º", "class_name": "b"})
    assert r.status_code == 200, r.text
    assert sent[-1]["student_number"] == "a12345" and sent[-1]["class_name"] == "B" and sent[-1]["email"] == ""
    # Staff still need an email
    r = await client.post(f"{api}/auth/no-access-contact", json={"profile": "docente", "name": "X", "message": "Y"})
    assert r.status_code == 400


async def test_own_profile_name(client, people, api):
    h = people["tec2"]["h"]
    r = await client.put(f"{api}/users/me/profile", headers=h, json={"display_name": "  Rui   Silva Docente-550 - Informática ", "phone": "912345678"})
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["display_name"] == "Rui Silva Docente-550 - Informática" and me["name_locked"] and me["phone"] == "912345678"
    assert (await client.put(f"{api}/users/me/profile", headers=h, json={"display_name": "R"})).status_code == 400
    me = (await client.put(f"{api}/users/me/profile", headers=h, json={"reset_name": True})).json()
    assert me["display_name"] == "Rui Técnico" and not me["name_locked"]


async def test_weekly_resolved_never_exceeds_created(client, people, api):
    weekly = (await client.get(f"{api}/admin/stats", headers=people["adm"]["h"])).json()["weekly"]
    assert all(w["resolved"] <= w["created"] for w in weekly)


async def test_news_popup(client, people, api):
    public = (await client.get(f"{api}/settings/public")).json()
    assert public["news_enabled"] is False and len(public["news_items"]) == 5
    r = await client.put(f"{api}/settings/news", headers=people["adm"]["h"], json={
        "enabled": True, "audience": "all", "title": "Novidades", "items": [{"icon": "star", "title": "Avalie", "text": "x"}], "republish": True,
    })
    assert r.status_code == 200 and r.json()["news_id"] == 2
    assert (await client.put(f"{api}/settings/news", headers=people["prof"]["h"], json={"items": []})).status_code == 403
    me = (await client.get(f"{api}/users/me", headers=people["prof"]["h"])).json()
    assert me["news_seen"] == 0
    assert (await client.put(f"{api}/users/me/news-seen", headers=people["prof"]["h"], json={"news_id": 2})).status_code == 204
    assert (await client.get(f"{api}/users/me", headers=people["prof"]["h"])).json()["news_seen"] == 2


async def test_mailbox_reply_forward_delete(client, people, api, monkeypatch):
    from app.services import mailbox as mb
    calls = []

    class Fake:
        name = "graph"
        can_archive = True

        async def reply(self, mid, text, reply_all=False):
            calls.append(("reply", mid, text, reply_all))

        async def forward(self, mid, recipients, text):
            calls.append(("forward", mid, recipients, text))

        async def delete(self, mid):
            calls.append(("delete", mid))

        async def set_read(self, mid, read):
            pass

    monkeypatch.setattr(mb, "get_provider", lambda: Fake())
    tec = people["tec"]["h"]
    assert (await client.post(f"{api}/mailbox/reply", headers=tec, json={"id": "m9", "text": "  "})).status_code == 400
    r = await client.post(f"{api}/mailbox/reply", headers=tec, json={"id": "m9", "text": "Obrigado, já tratámos.", "reply_all": True})
    assert r.status_code == 204
    assert calls[-1][0] == "reply" and calls[-1][3] is True and "Tiago Costa" in calls[-1][2]  # signed by who answered
    r = await client.post(f"{api}/mailbox/forward", headers=tec, json={"id": "m9", "to": ["prof@escola.pt", "externo@gmail.com"], "text": "Para conhecimento"})
    assert r.status_code == 204
    assert calls[-1][2] == [("prof@escola.pt", people and "Maria Serra Docente-510 - Física e Química"), ("externo@gmail.com", "")]
    assert (await client.post(f"{api}/mailbox/forward", headers=tec, json={"id": "m9", "to": ["não-é-email"]})).status_code == 400
    assert (await client.post(f"{api}/mailbox/delete", headers=tec, json={"id": "m9"})).status_code == 204
    assert calls[-1] == ("delete", "m9")
    # Only the support team sends from the helpdesk address
    assert (await client.post(f"{api}/mailbox/reply", headers=people["prof"]["h"], json={"id": "m9", "text": "x"})).status_code == 403


async def test_inactivity_never_closes_a_ticket_waiting_for_the_team(client, people, api, outbox):  # noqa: F811
    from datetime import datetime
    from sqlalchemy import text
    from app.database import AsyncSessionLocal
    from app.services import inactivity_service

    waiting_user = await _new_ticket(client, people, api, "Equipa respondeu por último")
    waiting_team = await _new_ticket(client, people, api, "Docente respondeu por último")
    for tid in (waiting_user, waiting_team):
        await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "Já reiniciou o computador?"})
    await client.post(f"{api}/tickets/{waiting_team}/comments", headers=people["prof"]["h"], json={"body": "Sim, continua igual."})

    async def age(sql, days):
        async with AsyncSessionLocal() as db:
            await db.execute(text(sql), {"ids": f"{waiting_user},{waiting_team}", "t": datetime.utcnow() - timedelta(days=days)})
            await db.commit()

    async def run():
        async with AsyncSessionLocal() as db:
            await inactivity_service.run_inactivity_check(db)

    async def status(tid):
        return (await client.get(f"{api}/tickets/{tid}", headers=people["tec"]["h"])).json()["status"]

    in_ids = "instr(',' || :ids || ',', ',' || {col} || ',') > 0"
    await age("UPDATE tickets SET updated_at = :t WHERE " + in_ids.format(col="id"), 8)
    outbox.clear()
    await run()
    # Team replied last: the requester is warned. Docente replied last: the team is asked where things stand
    asked = [(to, data) for to, ev, data in outbox if ev == "status_request"]
    assert {to for to, _ in asked} >= {"tec@escola.pt"} and "prof@escola.pt" not in {to for to, _ in asked}
    assert all(d["id"] == waiting_team and d["last_message"] == "Sim, continua igual." for _, d in asked)
    assert [(to, d["id"]) for to, ev, d in outbox if ev == "status_followup"] == [("prof@escola.pt", waiting_team)]
    outbox.clear()
    await run()
    assert not [1 for _, ev, d in outbox if ev == "status_request" and d["id"] == waiting_team]  # once a week only

    await age("UPDATE ticket_events SET created_at = :t WHERE event_type = 'inactivity_warning' AND " + in_ids.format(col="ticket_id"), 3)
    await age("UPDATE tickets SET updated_at = :t WHERE " + in_ids.format(col="id"), 10)
    await run()
    assert await status(waiting_user) == "closed"
    assert await status(waiting_team) != "closed"
