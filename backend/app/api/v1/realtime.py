import asyncio
import json
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services import realtime
from app.services.jwt_service import decode_token
from app.services.permissions import has_perm, permissions_for

router = APIRouter(prefix="/realtime", tags=["realtime"])


class ClientMessage(BaseModel):
    type: str
    ticket_id: int | None = None
    conversation_id: int | None = None
    private_to: int | None = None
    internal: bool = False


async def _can_view_ticket(db: AsyncSession, user: User, ticket_id: int) -> bool:
    from app.api.v1.tickets import _can_access_ticket
    from app.services import ticket_service
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        return False
    return _can_access_ticket(ticket, user) or has_perm(user, "tickets.view_all")


async def handle_client_message(db: AsyncSession, user: User, msg: ClientMessage, allowed_tickets: set[int]) -> None:
    """Messages sent by the browser: which ticket it is looking at, and "is typing" signals."""
    if msg.type == "view" and msg.ticket_id:
        if msg.ticket_id in allowed_tickets or await _can_view_ticket(db, user, msg.ticket_id):
            allowed_tickets.add(msg.ticket_id)
            realtime.view_ticket(user.id, msg.ticket_id)
    elif msg.type == "leave" and msg.ticket_id:
        realtime.leave_ticket(user.id, msg.ticket_id)
    elif msg.type == "typing" and msg.ticket_id in allowed_tickets:
        viewers = realtime.ticket_viewers(msg.ticket_id) - {user.id}
        if msg.private_to:
            viewers &= {msg.private_to}
        elif msg.internal:
            rows = (await db.execute(select(User).where(User.id.in_(viewers or {0})))).scalars().all()
            viewers = {u.id for u in rows if "tickets.manage" in permissions_for(u)}
        realtime.publish(viewers, {
            "type": "ticket.typing", "ticket_id": msg.ticket_id,
            "user": {"id": user.id, "name": user.display_name}, "private": bool(msg.private_to),
        })
    elif msg.type == "chat.typing" and msg.conversation_id:
        from app.services import chat_service
        members = await chat_service.member_ids(db, msg.conversation_id)
        if user.id in members:
            realtime.publish(members - {user.id}, {
                "type": "chat.typing", "conversation_id": msg.conversation_id,
                "user": {"id": user.id, "name": user.display_name},
            })


@router.websocket("/ws")
async def websocket(ws: WebSocket, token: str = Query("")):
    payload = decode_token(token) if token else None
    if not payload or not payload.get("sub"):
        await ws.close(code=4401)
        return
    async with AsyncSessionLocal() as db:
        user = await db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        await ws.close(code=4401)
        return
    await ws.accept()
    realtime.remember_name(user.id, user.display_name)
    queue = realtime.register(user.id)
    allowed_tickets: set[int] = set()
    await ws.send_json({"type": "hello", "seq": realtime.current_seq()})

    async def sender():
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=25)
            except asyncio.TimeoutError:
                item = {"type": "ping"}
            await ws.send_json(item)

    send_task = asyncio.create_task(sender())
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = ClientMessage(**json.loads(raw))
            except Exception:
                continue
            if msg.type == "ping":
                continue
            async with AsyncSessionLocal() as db:
                fresh = await db.get(User, user.id)
                if fresh and fresh.is_active:
                    await handle_client_message(db, fresh, msg, allowed_tickets)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        send_task.cancel()
        realtime.unregister(user.id, queue)


# ── Fallback for networks/proxies that block WebSockets ────────────────────

_poll_allowed: dict[int, set[int]] = {}


@router.get("/poll")
async def poll(after: int = Query(0, ge=0), current_user: User = Depends(get_current_user)):
    realtime.remember_name(current_user.id, current_user.display_name)
    realtime.mark_polled(current_user.id)
    if after == 0:
        return {"seq": realtime.current_seq(), "events": []}
    events = realtime.events_after(current_user.id, after)
    return {"seq": events[-1]["seq"] if events else after, "events": events}


@router.post("/send", status_code=204)
async def send(msg: ClientMessage, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    realtime.mark_polled(current_user.id)
    allowed = _poll_allowed.setdefault(current_user.id, set())
    await handle_client_message(db, current_user, msg, allowed)
