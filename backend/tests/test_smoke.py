"""Smoke tests for the rules that matter most: access, private messages, deleting tickets and backups."""
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _new_ticket(client, people, api, title="Projetor não liga"):
    cats = (await client.get(f"{api}/categories", headers=people["adm"]["h"])).json()
    schools = (await client.get(f"{api}/schools", headers=people["adm"]["h"])).json()
    r = await client.post(f"{api}/tickets", headers=people["prof"]["h"], json={
        "title": title, "description": "Desde ontem.", "category_id": cats[0]["id"], "school_id": schools[0]["id"],
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_health_and_me(client, people, api):
    assert (await client.get("/health")).json() == {"status": "ok"}
    me = (await client.get(f"{api}/users/me", headers=people["tec"]["h"])).json()
    assert me["display_name"] == "Tiago Costa"
    assert (await client.get(f"{api}/users/me", headers={"Authorization": "Bearer x.y.z"})).status_code == 401


async def test_teacher_cannot_change_status(client, people, api):
    tid = await _new_ticket(client, people, api)
    r = await client.patch(f"{api}/tickets/{tid}", headers=people["prof"]["h"], json={"status": "closed"})
    assert r.status_code == 403
    r = await client.patch(f"{api}/tickets/{tid}", headers=people["tec"]["h"], json={"status": "in_progress"})
    assert r.status_code == 200


async def test_private_message_to_several_people(client, people, api):
    tid = await _new_ticket(client, people, api, "Privado")
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={
        "body": "segredo partilhado", "private_to_ids": [people["tec2"]["id"], people["dir"]["id"]],
    })
    assert r.status_code == 201, r.text

    async def sees(who):
        t = (await client.get(f"{api}/tickets/{tid}", headers=people[who]["h"])).json()
        return any(c["body"] == "segredo partilhado" for c in t.get("comments", []))

    assert await sees("tec") and await sees("tec2") and await sees("dir")
    assert not await sees("prof") and not await sees("adm")
    # The Direção answers the conversation privately, but may not write in public
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["dir"]["h"], json={
        "body": "ok", "private_to_ids": [people["tec"]["id"], people["tec2"]["id"]],
    })
    assert r.status_code == 201
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["dir"]["h"], json={"body": "público"})
    assert r.status_code == 403
    # A docente cannot start a private conversation with a technician
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["prof"]["h"], json={
        "body": "x", "private_to_ids": [people["tec2"]["id"]],
    })
    assert r.status_code == 403


async def test_delete_ticket_removes_everything(client, people, api):
    from datetime import datetime, timedelta, timezone
    tid = await _new_ticket(client, people, api, "Para apagar")
    r = await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": "resposta"})
    cid = r.json()["id"]
    await client.post(f"{api}/reactions/toggle", headers=people["prof"]["h"], json={"target_type": "comment", "target_id": cid, "emoji": "👍"})
    when = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert (await client.put(f"{api}/tickets/{tid}/reminders/mine", headers=people["tec"]["h"], json={"remind_at": when})).status_code == 200
    r = await client.post(f"{api}/admin/tickets/bulk-action", headers=people["adm"]["h"], json={"ids": [tid], "action": "delete"})
    assert r.json() == {"affected": 1}

    from sqlalchemy import text
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        for table, col in (("ticket_reminders", "ticket_id"), ("comments", "ticket_id"), ("ticket_events", "ticket_id")):
            n = (await db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {col} = :t"), {"t": tid})).scalar_one()
            assert n == 0, table
        n = (await db.execute(text("SELECT COUNT(*) FROM reactions WHERE target_type='comment' AND target_id=:c"), {"c": cid})).scalar_one()
        assert n == 0
    # Reminders keep working after a deleted ticket
    from app.services import reminder_service
    async with AsyncSessionLocal() as db:
        await reminder_service.send_due_reminders(db)


async def test_json_backup_round_trip(client, people, api):
    await _new_ticket(client, people, api, "Antes do backup")
    backup = (await client.get(f"{api}/admin/backup", headers=people["adm"]["h"])).json()
    assert backup["format"] == 2 and "roles" in backup and "comment_private_recipients" in backup
    await _new_ticket(client, people, api, "Depois do backup")
    import json
    r = await client.post(f"{api}/admin/backup/restore/json", headers=people["adm"]["h"],
                          files={"file": ("b.json", json.dumps(backup), "application/json")})
    assert r.status_code == 200, r.text
    titles = [t["title"] for t in (await client.get(f"{api}/tickets", params={"size": 100}, headers=people["tec"]["h"])).json()["items"]]
    assert "Antes do backup" in titles and "Depois do backup" not in titles


async def test_overdue_filter_and_reactions_batch(client, people, api):
    r = await client.get(f"{api}/tickets", params={"overdue": True}, headers=people["tec"]["h"])
    assert r.status_code == 200
    tid = await _new_ticket(client, people, api, "Reações")
    ids = []
    for i in range(5):
        ids.append((await client.post(f"{api}/tickets/{tid}/comments", headers=people["tec"]["h"], json={"body": f"r{i}"})).json()["id"])
    r = await client.get(f"{api}/reactions", params={"target_type": "comment", "ids": ",".join(map(str, ids))}, headers=people["prof"]["h"])
    assert sorted(map(int, r.json())) == sorted(ids)
