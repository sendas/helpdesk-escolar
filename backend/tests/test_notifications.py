"""Who gets an email, and what the support company receives."""
import pytest

from tests.test_smoke import _new_ticket

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    from app.config import settings
    from app.services import email_service

    async def fake(to, event, data):
        sent.append((to, event, data))

    monkeypatch.setattr(settings, "mail_server", "smtp.test")
    monkeypatch.setattr(email_service, "send_ticket_notification", fake)
    monkeypatch.setattr(email_service, "send_ticket_email_now", fake)

    async def fake_provider(to, event, data, thread_id, first):
        sent.append((to, event, {**data, "thread_id": thread_id, "first": first}))

    monkeypatch.setattr(email_service, "send_provider_email", fake_provider)
    return sent


async def test_state_changes_only_tell_the_requester_when_it_concerns_them(client, people, api, outbox):
    tid = await _new_ticket(client, people, api, "Estados")
    # tec2 (team) follows the ticket; tec changes the state
    await client.post(f"{api}/tickets/{tid}/watchers", headers=people["tec"]["h"], json={"user_id": people["tec2"]["id"]})
    outbox.clear()
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "in_progress"})
    assert outbox == []
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "waiting_user"})
    assert [(to, ev) for to, ev, _ in outbox] == [("prof@escola.pt", "updated")]
    outbox.clear()
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"priority": "high"})
    assert outbox == []


async def test_reply_with_state_is_one_email(client, people, api, outbox):
    tid = await _new_ticket(client, people, api, "Resposta e estado")
    outbox.clear()
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "Já está.", "new_status": "resolved"})
    assert r.status_code == 201, r.text
    to_prof = [(ev, d) for to, ev, d in outbox if to == "prof@escola.pt"]
    assert len(to_prof) == 1 and to_prof[0][0] == "commented" and to_prof[0][1]["new_status"] == "Resolvido"
    assert not any(to == "tec@escola.pt" for to, _, _ in outbox)
    t = (await client.get(f"{api}/tickets/{tid}", headers=people["tec"]["h"])).json()
    assert t["status"] == "resolved"
    # A docente cannot change the state this way
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["prof"]["h"], json={"body": "x", "new_status": "closed"})
    assert r.status_code == 403


async def test_preferences_switch_off_state_emails(client, people, api, outbox):
    r = await client.put(f"{api}/users/me/notifications", headers=people["prof"]["h"], json={"prefs": {"status": {"email": False}}})
    assert r.json()["prefs"]["status"]["email"] is False
    tid = await _new_ticket(client, people, api, "Sem avisos de estado")
    outbox.clear()
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "closed"})
    assert not any(to == "prof@escola.pt" for to, _, _ in outbox)
    await client.put(f"{api}/users/me/notifications", headers=people["prof"]["h"], json={"prefs": {}})


async def test_support_company_gets_the_conversation(client, people, api, outbox):
    from app.api.v1.settings import _update_settings
    _update_settings({"support_provider_email": "apoio@empresa.pt", "support_provider_name": "Empresa X"})
    tid = await _new_ticket(client, people, api, "Para a empresa")
    await client.post(f"{api}/tickets/{tid}/comments", headers=people["prof"]["h"], json={"body": "Continua sem ligar."})
    await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "Já testei outro cabo."})
    await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "nota interna", "is_internal": True})
    await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "privado", "private_to_ids": [people["tec2"]["id"]]})
    outbox.clear()
    r = await client.post(f"{api}/tickets/{tid}/escalate", headers=people["tec"]["h"])
    assert r.status_code == 200, r.text
    mails = [(ev, d) for to, ev, d in outbox if to == "apoio@empresa.pt"]
    assert len(mails) == 1 and mails[0][0] == "escalated"
    bodies = [m["body"] for m in mails[0][1]["conversation"]]
    assert bodies == ["Continua sem ligar.", "Já testei outro cabo."]
    thread = mails[0][1]["thread_id"]
    assert mails[0][1]["first"] and thread.startswith("<helpdesk-")
    # Reporting it again would open a duplicate on their side
    assert (await client.post(f"{api}/tickets/{tid}/escalate", headers=people["tec"]["h"])).status_code == 400
    # Ordinary replies are not sent to the company
    outbox.clear()
    reply = (await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "Pode verificar a fonte?"})).json()
    assert not any(to == "apoio@empresa.pt" for to, _, _ in outbox)
    # …only when sent on purpose, as a reply in the same email conversation, with the history
    r = await client.post(f"{api}/tickets/{tid}/comments/{reply['id']}/escalate", headers=people["tec"]["h"])
    assert r.status_code == 204
    mails = [(ev, d) for to, ev, d in outbox if to == "apoio@empresa.pt"]
    assert len(mails) == 1 and mails[0][0] == "supplier_comment" and mails[0][1]["comment"] == "Pode verificar a fonte?"
    assert mails[0][1]["thread_id"] == thread and not mails[0][1]["first"]
    assert [m["body"] for m in mails[0][1]["conversation"]] == ["Continua sem ligar.", "Já testei outro cabo."]
    # Priority changes do not go to the company; solving it does, once, in the same conversation
    outbox.clear()
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"priority": "urgent"})
    assert not any(to == "apoio@empresa.pt" for to, _, _ in outbox)
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "resolved"})
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "closed"})
    mails = [(ev, d) for to, ev, d in outbox if to == "apoio@empresa.pt"]
    assert [ev for ev, _ in mails] == ["supplier_updated"] and mails[0][1]["thread_id"] == thread
    t = (await client.get(f"{api}/tickets/{tid}", headers=people["tec"]["h"])).json()
    assert t["is_escalated"] is False
    # "Reverter": reported again without a new email (they already have this ticket)
    outbox.clear()
    assert (await client.post(f"{api}/tickets/{tid}/escalate", headers=people["tec"]["h"])).status_code == 200
    assert not any(to == "apoio@empresa.pt" for to, _, _ in outbox)


async def test_email_templates_render(client):
    from app.services.email_service import jinja_env
    conv = [{"author": "A", "when": "29/09/2026 10:00", "body": "<b>olá</b>"}]
    for name in ("ticket_escalated.html", "ticket_supplier_comment.html", "ticket_supplier_updated.html", "ticket_commented.html"):
        html = jinja_env.get_template(name).render(id=1, title="T", provider="P", conversation=conv, attachments=["a.pdf"],
                                                   comment="c", author="A", new_status="Resolvido", status="Fechado", editor="E",
                                                   description="d", requester="R", requester_email="r@x", category="C",
                                                   priority="Alta", school="S", escalated_by="E", ticket_url="http://x")
        assert "&lt;b&gt;olá&lt;/b&gt;" in html or name == "ticket_commented.html"


async def test_support_company_number_goes_in_later_subjects(client, people, api, outbox):
    from app.api.v1.settings import _update_settings
    from app.database import AsyncSessionLocal
    from app.services import email_ingest
    _update_settings({"support_provider_email": "suporte@controlink.pt", "support_provider_name": "Controlink"})
    tid = await _new_ticket(client, people, api, "Switch da sala de DTs")
    assert (await client.post(f"{api}/tickets/{tid}/escalate", headers=people["tec"]["h"])).status_code == 200
    # Their helpdesk answers from another address of the company, with its own number in the subject
    msg = email_ingest._parse_graph_message({
        "subject": f"RE: [Ticket #{tid}] Switch da sala de DTs (#8591)",
        "from": {"emailAddress": {"address": "notifications=controlink.pt@mg.controlink.pt"}},
        "body": {"contentType": "text", "content": "Um switch de quantas portas?"},
        "internetMessageId": f"<controlink-{tid}@mg.controlink.pt>",
    })
    assert msg["provider_ref"] == "8591"
    async with AsyncSessionLocal() as db:
        await email_ingest._import_messages(db, [msg])
    t = (await client.get(f"{api}/tickets/{tid}", headers=people["tec"]["h"])).json()
    assert t["provider_ref"] == "8591"
    outbox.clear()
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "resolved"})
    mails = [d for to, ev, d in outbox if to == "suporte@controlink.pt"]
    assert len(mails) == 1 and mails[0]["provider_ref"] == "8591" and not mails[0]["first"]
    # Our own marker is never taken for theirs; a technician can also type it
    assert email_ingest._provider_ref(f"[Ticket #{tid}] Teste") is None
    r = await client.put(f"{api}/tickets/{tid}/provider-ref", headers=people["tec"]["h"], json={"ref": "#8600"})
    assert r.status_code == 200 and r.json()["provider_ref"] == "8600"
    assert (await client.put(f"{api}/tickets/{tid}/provider-ref", headers=people["prof"]["h"], json={"ref": "1"})).status_code == 403
