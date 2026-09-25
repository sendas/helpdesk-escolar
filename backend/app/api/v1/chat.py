from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, require_perm
from app.models.chat import ChatConversation, ChatMember, ChatMessage, SupportAgentStatus
from app.models.user import User
from app.services import chat_service, realtime
from app.services.permissions import has_perm, permissions_for

router = APIRouter(prefix="/chat", tags=["chat"])


class MessageCreate(BaseModel):
    body: str


class DirectCreate(BaseModel):
    user_id: int


class GroupCreate(BaseModel):
    title: str
    member_ids: list[int]


class GroupUpdate(BaseModel):
    title: str | None = None
    member_ids: list[int] | None = None


class SupportStart(BaseModel):
    body: str
    school_id: int | None = None


class SupportConvert(BaseModel):
    title: str | None = None
    category_id: int | None = None


class Availability(BaseModel):
    available: bool


def _clean(body: str) -> str:
    text = (body or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escreva uma mensagem.")
    return text[:4000]


async def _conversation_for(db: AsyncSession, conv_id: int, user: User) -> ChatConversation:
    """The conversation, if the user may read it: members always; support chats also by support responders."""
    conv = await db.get(ChatConversation, conv_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    is_member = any(m.user_id == user.id for m in conv.members)
    if is_member and conv.kind != "support" and not has_perm(user, "chat.team"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso ao chat da equipa.")
    if not is_member and not (conv.kind == "support" and has_perm(user, "chat.support")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    return conv


# ── Team chat ────────────────────────────────────────────────────────────

@router.get("/people")
async def chat_people(db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.team"))):
    users = (await db.execute(select(User).where(User.is_active.is_(True), User.id != me.id).order_by(User.display_name))).scalars().all()
    return [{**chat_service.user_brief(u), "online": realtime.is_online(u.id)} for u in users if "chat.team" in permissions_for(u)]


@router.get("/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    if has_perm(me, "chat.team"):
        await chat_service.sync_role_groups(db)
    ids = select(ChatMember.conversation_id).where(ChatMember.user_id == me.id)
    query = select(ChatConversation).where(ChatConversation.id.in_(ids))
    if not has_perm(me, "chat.team"):
        query = query.where(ChatConversation.kind == "support")
    convs = (await db.execute(query.order_by(ChatConversation.updated_at.desc()))).scalars().all()
    return [await chat_service.serialize_conversation(db, c, me) for c in convs if c.kind != "support" or has_perm(me, "chat.support")]


@router.get("/unread")
async def unread_count(db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    """Unread messages in team chats (support chats are counted in the support queue)."""
    if not has_perm(me, "chat.team"):
        return {"unread": 0}
    ids = select(ChatMember.conversation_id).where(ChatMember.user_id == me.id)
    convs = (await db.execute(select(ChatConversation).where(ChatConversation.id.in_(ids), ChatConversation.kind != "support"))).scalars().all()
    total = 0
    for c in convs:
        total += (await chat_service.serialize_conversation(db, c, me))["unread"]
    return {"unread": total}


@router.post("/conversations/direct")
async def open_direct(data: DirectCreate, db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.team"))):
    other = await db.get(User, data.user_id)
    if not other or not other.is_active or other.id == me.id or not has_perm(other, "chat.team"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta pessoa não usa o chat da equipa.")
    conv = await chat_service.get_or_create_direct(db, me, other)
    return await chat_service.serialize_conversation(db, conv, me)


@router.post("/conversations/group")
async def create_group(data: GroupCreate, db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.team"))):
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dê um nome ao grupo.")
    people = (await db.execute(select(User).where(User.id.in_(set(data.member_ids) | {me.id})))).scalars().all()
    people = [u for u in people if u.is_active and has_perm(u, "chat.team")]
    conv = ChatConversation(kind="group", title=title[:200], created_by_id=me.id, members=[ChatMember(user_id=u.id) for u in people])
    db.add(conv)
    await db.commit()
    await chat_service.post_message(db, conv, None, f"{me.display_name} criou o grupo.", system=True)
    return await chat_service.serialize_conversation(db, conv, me)


@router.patch("/conversations/{conv_id}")
async def update_group(conv_id: int, data: GroupUpdate, db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.team"))):
    conv = await _conversation_for(db, conv_id, me)
    if conv.kind != "group" or conv.role_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este grupo é gerido automaticamente pelo papel.")
    if conv.created_by_id != me.id and not has_perm(me, "users.manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só quem criou o grupo o pode alterar.")
    before = {m.user_id for m in conv.members}
    if data.title and data.title.strip():
        conv.title = data.title.strip()[:200]
    if data.member_ids is not None:
        people = (await db.execute(select(User).where(User.id.in_(set(data.member_ids) | {conv.created_by_id or me.id})))).scalars().all()
        wanted = {u.id for u in people if u.is_active and has_perm(u, "chat.team")}
        current = {m.user_id: m for m in conv.members}
        for uid in wanted - set(current):
            conv.members.append(ChatMember(user_id=uid))
        for uid in set(current) - wanted:
            conv.members.remove(current[uid])
    await db.commit()
    realtime.publish(before | {m.user_id for m in conv.members}, {"type": "chat.conversation", "conversation_id": conv.id})
    return await chat_service.serialize_conversation(db, conv, me)


@router.get("/conversations/{conv_id}/messages")
async def list_messages(conv_id: int, before: int | None = Query(None), limit: int = Query(50, ge=1, le=200),
                        db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    conv = await _conversation_for(db, conv_id, me)
    query = select(ChatMessage).where(ChatMessage.conversation_id == conv.id)
    if before:
        query = query.where(ChatMessage.id < before)
    rows = (await db.execute(query.order_by(ChatMessage.id.desc()).limit(limit))).scalars().all()
    return {"conversation": await chat_service.serialize_conversation(db, conv, me),
            "messages": [chat_service.serialize_message(m) for m in reversed(rows)]}


@router.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: int, data: MessageCreate, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    conv = await _conversation_for(db, conv_id, me)
    if conv.kind == "support":
        if conv.support_status not in ("waiting", "active"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta conversa de apoio já terminou.")
        if me.id != conv.requester_id:
            # A responder writing first takes the conversation
            if conv.support_status == "waiting":
                await chat_service.accept_support(db, conv, me)
            elif conv.agent_id != me.id and not any(m.user_id == me.id for m in conv.members):
                conv.members.append(ChatMember(user_id=me.id))
                await db.commit()
    msg = await chat_service.post_message(db, conv, me, _clean(data.body))
    return chat_service.serialize_message(msg)


@router.post("/conversations/{conv_id}/read", status_code=204)
async def mark_read(conv_id: int, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    conv = await _conversation_for(db, conv_id, me)
    for m in conv.members:
        if m.user_id == me.id:
            m.last_read_at = datetime.utcnow()
    await db.commit()
    members = {m.user_id for m in conv.members}
    realtime.publish(members, {"type": "chat.read", "conversation_id": conv.id, "user_id": me.id, "at": datetime.utcnow().isoformat() + "Z"})


# ── Live support ─────────────────────────────────────────────────────────

@router.get("/support/status")
async def support_status(db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    cfg = chat_service.support_settings()
    conv = await chat_service.active_support_for(db, me)
    agents_online = len({a for a in await chat_service.available_agents(db) if realtime.is_online(a)})
    mine = None
    if has_perm(me, "chat.support"):
        row = await db.get(SupportAgentStatus, me.id)
        mine = bool(row and row.available)
    return {
        "enabled": cfg["enabled"], "open_now": chat_service.support_open_now(), "hours": cfg["hours"],
        "hours_text": chat_service.support_hours_text(), "wait_minutes": cfg["wait_minutes"],
        "agents_online": agents_online, "conversation_id": conv.id if conv else None,
        "is_responder": has_perm(me, "chat.support"), "available": mine,
    }


@router.get("/support/mine")
async def my_support(db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    """The requester's latest support conversation (active, or the last one, so they can still read it)."""
    conv = await chat_service.active_support_for(db, me)
    if not conv:
        conv = (await db.execute(select(ChatConversation).where(
            ChatConversation.kind == "support", ChatConversation.requester_id == me.id).order_by(ChatConversation.id.desc()))).scalars().first()
    if not conv:
        return None
    rows = (await db.execute(select(ChatMessage).where(ChatMessage.conversation_id == conv.id).order_by(ChatMessage.id))).scalars().all()
    return {"conversation": await chat_service.serialize_conversation(db, conv, me), "messages": [chat_service.serialize_message(m) for m in rows]}


@router.post("/support/start")
async def start_support(data: SupportStart, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    if not chat_service.support_settings()["enabled"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O apoio ao vivo está desativado.")
    conv = await chat_service.start_support(db, me, _clean(data.body), data.school_id)
    return await my_support(db, me)


@router.get("/support/queue")
async def support_queue(db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.support"))):
    convs = (await db.execute(select(ChatConversation).where(
        ChatConversation.kind == "support", ChatConversation.support_status.in_(["waiting", "active"]),
    ).order_by(ChatConversation.created_at))).scalars().all()
    return [await chat_service.serialize_conversation(db, c, me) for c in convs]


@router.put("/support/availability")
async def set_availability(data: Availability, db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.support"))):
    row = await db.get(SupportAgentStatus, me.id)
    if not row:
        row = SupportAgentStatus(user_id=me.id)
        db.add(row)
    row.available = data.available
    row.updated_at = datetime.utcnow()
    await db.commit()
    await chat_service.notify_queue(db)
    return {"available": row.available}


@router.post("/support/{conv_id}/accept")
async def accept(conv_id: int, db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.support"))):
    conv = await _conversation_for(db, conv_id, me)
    if conv.kind != "support":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não é uma conversa de apoio.")
    if conv.support_status != "waiting":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Outro técnico já está a responder a este pedido.")
    await chat_service.accept_support(db, conv, me)
    return await chat_service.serialize_conversation(db, conv, me)


@router.post("/support/{conv_id}/close")
async def close(conv_id: int, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    conv = await _conversation_for(db, conv_id, me)
    if conv.kind != "support" or not (me.id == conv.requester_id or has_perm(me, "chat.support")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não pode terminar esta conversa.")
    await chat_service.close_support(db, conv, me)
    return await chat_service.serialize_conversation(db, conv, me)


@router.post("/support/{conv_id}/convert")
async def convert(conv_id: int, data: SupportConvert, db: AsyncSession = Depends(get_db), me: User = Depends(require_perm("chat.support"))):
    conv = await _conversation_for(db, conv_id, me)
    if conv.kind != "support" or conv.ticket_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta conversa já foi convertida ou não é de apoio.")
    ticket = await chat_service.convert_to_ticket(db, conv, me, title=data.title, category_id=data.category_id)
    return {"ticket_id": ticket.id if ticket else None}
