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
    # A later reply goes with the history
    outbox.clear()
    await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "Pode verificar a fonte?"})
    mails = [(ev, d) for to, ev, d in outbox if to == "apoio@empresa.pt"]
    assert mails[0][0] == "supplier_comment" and mails[0][1]["comment"] == "Pode verificar a fonte?"
    assert [m["body"] for m in mails[0][1]["conversation"]] == ["Continua sem ligar.", "Já testei outro cabo."]
    # Priority changes no longer go to the company; closing does
    outbox.clear()
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"priority": "urgent"})
    assert not any(to == "apoio@empresa.pt" for to, _, _ in outbox)
    await client.patch(f"{api}/admin/tickets/{tid}", headers=people["tec"]["h"], json={"status": "closed"})
    assert [ev for to, ev, _ in outbox if to == "apoio@empresa.pt"] == ["supplier_updated"]


async def test_email_templates_render(client):
    from app.services.email_service import jinja_env
    conv = [{"author": "A", "when": "29/09/2026 10:00", "body": "<b>olá</b>"}]
    for name in ("ticket_escalated.html", "ticket_supplier_comment.html", "ticket_supplier_updated.html", "ticket_commented.html"):
        html = jinja_env.get_template(name).render(id=1, title="T", provider="P", conversation=conv, attachments=["a.pdf"],
                                                   comment="c", author="A", new_status="Resolvido", status="Fechado", editor="E",
                                                   description="d", requester="R", requester_email="r@x", category="C",
                                                   priority="Alta", school="S", escalated_by="E", ticket_url="http://x")
        assert "&lt;b&gt;olá&lt;/b&gt;" in html or name == "ticket_commented.html"
