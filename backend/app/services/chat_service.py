"""Team chat (direct and group conversations) and live support (balão de apoio)."""
import asyncio
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.category import Category
from app.models.chat import ChatConversation, ChatMember, ChatMessage, SupportAgentStatus
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.services import realtime
from app.services.permissions import effective_role_key, permissions_for

_LISBON = ZoneInfo("Europe/Lisbon")
WEEKDAYS = {"1": "segunda", "2": "terça", "3": "quarta", "4": "quinta", "5": "sexta", "6": "sábado", "7": "domingo"}


# ── Helpers ──────────────────────────────────────────────────────────────

def short_name(name: str | None) -> str:
    """"Maria Leonor Marinho Nunes Serra Docente-510 - Física e Química" → "Maria Serra" (as in the frontend)."""
    import re
    base = re.split(r"\s+(?:Docente|Não Docente|Nao Docente|Funcionári[oa])[-\s]", name or "", flags=re.I)[0].split(" - ")[0].strip()
    parts = base.split()
    return f"{parts[0]} {parts[-1]}" if len(parts) > 2 else base

def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def user_brief(user: User | None) -> dict | None:
    if not user:
        return None
    return {"id": user.id, "display_name": user.display_name, "role_label": user.role_label}


async def member_ids(db: AsyncSession, conversation_id: int) -> set[int]:
    rows = await db.execute(select(ChatMember.user_id).where(ChatMember.conversation_id == conversation_id))
    return {r[0] for r in rows}


def serialize_message(msg: ChatMessage) -> dict:
    return {
        "id": msg.id, "conversation_id": msg.conversation_id, "body": msg.body, "is_system": msg.is_system,
        "created_at": _iso(msg.created_at), "author": user_brief(msg.author),
    }


async def serialize_conversation(db: AsyncSession, conv: ChatConversation, me: User) -> dict:
    last = (
        await db.execute(select(ChatMessage).where(ChatMessage.conversation_id == conv.id).order_by(ChatMessage.id.desc()).limit(1))
    ).scalar_one_or_none()
    mine = next((m for m in conv.members if m.user_id == me.id), None)
    unread = 0
    if mine:
        q = select(func.count()).select_from(ChatMessage).where(ChatMessage.conversation_id == conv.id, ChatMessage.author_id != me.id)
        if mine.last_read_at:
            q = q.where(ChatMessage.created_at > mine.last_read_at)
        unread = (await db.execute(q)).scalar_one()
    others = [m.user for m in conv.members if m.user_id != me.id]
    title = conv.title
    if conv.kind == "direct":
        title = others[0].display_name if others else "Conversa"
    elif conv.kind == "support":
        requester = await db.get(User, conv.requester_id) if conv.requester_id else None
        title = requester.display_name if requester and requester.id != me.id else "Apoio ao vivo"
    return {
        "id": conv.id, "kind": conv.kind, "title": title, "role_key": conv.role_key,
        "members": [user_brief(m.user) for m in conv.members],
        "last_message": serialize_message(last) if last else None,
        "unread": unread, "updated_at": _iso(conv.updated_at),
        "support_status": conv.support_status, "ticket_id": conv.ticket_id,
        "requester_id": conv.requester_id, "agent_id": conv.agent_id,
        "created_at": _iso(conv.created_at),
    }


async def _push_offline(user_ids: set[int], title: str, body: str, url: str) -> None:
    offline = {u for u in user_ids if not realtime.is_online(u)}
    if offline:
        from app.services import push_service
        asyncio.create_task(push_service.send_push_to_users_bg(offline, title, body[:120], url))


async def post_message(db: AsyncSession, conv: ChatConversation, author: User | None, body: str, system: bool = False) -> ChatMessage:
    msg = ChatMessage(conversation_id=conv.id, author_id=author.id if author else None, body=body.strip(), is_system=system)
    db.add(msg)
    conv.updated_at = datetime.utcnow()
    if author:
        for m in conv.members:
            if m.user_id == author.id:
                m.last_read_at = datetime.utcnow()
    await db.commit()
    msg = (await db.execute(select(ChatMessage).where(ChatMessage.id == msg.id))).scalar_one()
    members = await member_ids(db, conv.id)
    realtime.publish(members, {"type": "chat.message", "conversation_id": conv.id, "message": serialize_message(msg)})
    if author and not system:
        url = "/chat?c=%d" % conv.id
        await _push_offline(members - {author.id}, f"Mensagem de {short_name(author.display_name)}", body, url)
    return msg


def _notify_conversation(member_set: set[int], conv_id: int) -> None:
    realtime.publish(member_set, {"type": "chat.conversation", "conversation_id": conv_id})


# ── Team chat ────────────────────────────────────────────────────────────

_last_group_sync = 0.0


async def sync_role_groups(db: AsyncSession, force: bool = False) -> None:
    """Automatic group per papel that has the team chat permission, with everyone holding that papel."""
    global _last_group_sync
    if not force and time.time() - _last_group_sync < 60:
        return
    _last_group_sync = time.time()
    roles = (await db.execute(select(Role))).scalars().all()
    chat_roles = {r.key: r for r in roles if "chat.team" in (r.permissions or "").split(",")}
    users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
    by_role: dict[str, set[int]] = {}
    for u in users:
        if "chat.team" in permissions_for(u):
            by_role.setdefault(effective_role_key(u), set()).add(u.id)
    groups = (await db.execute(select(ChatConversation).where(ChatConversation.role_key.is_not(None)))).scalars().all()
    existing = {g.role_key: g for g in groups}
    changed = False
    for key, role in chat_roles.items():
        wanted = by_role.get(key, set())
        conv = existing.get(key)
        if not conv:
            if not wanted:
                continue
            conv = ChatConversation(kind="group", title=role.label, role_key=key, members=[])
            db.add(conv)
        conv.title = role.label
        current = {m.user_id: m for m in conv.members}
        for uid in wanted - set(current):
            conv.members.append(ChatMember(user_id=uid))
            changed = True
        for uid in set(current) - wanted:
            conv.members.remove(current[uid])
            changed = True
    for key, conv in existing.items():
        if key not in chat_roles and conv.members:
            conv.members.clear()
            changed = True
    await db.commit()
    if changed:
        realtime.publish(set().union(*by_role.values()) if by_role else set(), {"type": "chat.conversation"})


async def get_or_create_direct(db: AsyncSession, me: User, other: User) -> ChatConversation:
    mine = select(ChatMember.conversation_id).where(ChatMember.user_id == me.id)
    theirs = select(ChatMember.conversation_id).where(ChatMember.user_id == other.id)
    conv = (
        await db.execute(
            select(ChatConversation).where(ChatConversation.kind == "direct", ChatConversation.id.in_(mine), ChatConversation.id.in_(theirs))
        )
    ).scalars().first()
    if conv:
        return conv
    conv = ChatConversation(kind="direct", created_by_id=me.id, members=[ChatMember(user_id=me.id), ChatMember(user_id=other.id)])
    db.add(conv)
    await db.commit()
    return conv


# ── Live support ─────────────────────────────────────────────────────────

def support_settings() -> dict:
    from app.api.v1.settings import _read_settings
    s = _read_settings()
    return {"enabled": bool(s.get("support_chat_enabled", True)), "wait_minutes": int(s.get("support_wait_minutes", 5)),
            "hours": s.get("support_hours") or {}}


def support_open_now(now: datetime | None = None) -> bool:
    cfg = support_settings()
    if not cfg["enabled"]:
        return False
    now = now or datetime.now(_LISBON)
    day = cfg["hours"].get(str(now.isoweekday())) or {}
    hhmm = now.strftime("%H:%M")
    return bool(day.get("enabled")) and day.get("start", "") <= hhmm < day.get("end", "")


def support_hours_text() -> str:
    hours = support_settings()["hours"]
    parts = [f"{WEEKDAYS[d]} {hours[d]['start']}–{hours[d]['end']}" for d in sorted(hours) if hours[d].get("enabled")]
    return "; ".join(parts) or "sem horário definido"


async def responders(db: AsyncSession) -> list[User]:
    users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
    return [u for u in users if "chat.support" in permissions_for(u)]


async def available_agents(db: AsyncSession) -> set[int]:
    rows = await db.execute(select(SupportAgentStatus.user_id).where(SupportAgentStatus.available.is_(True)))
    return {r[0] for r in rows}


async def notify_queue(db: AsyncSession) -> None:
    realtime.publish({u.id for u in await responders(db)}, {"type": "support.queue"})


async def active_support_for(db: AsyncSession, requester: User) -> ChatConversation | None:
    return (
        await db.execute(
            select(ChatConversation).where(
                ChatConversation.kind == "support", ChatConversation.requester_id == requester.id,
                ChatConversation.support_status.in_(["waiting", "active"]),
            ).order_by(ChatConversation.id.desc())
        )
    ).scalars().first()


async def start_support(db: AsyncSession, requester: User, body: str, school_id: int | None) -> ChatConversation:
    conv = await active_support_for(db, requester)
    if conv:
        await post_message(db, conv, requester, body)
        return conv
    conv = ChatConversation(kind="support", support_status="waiting", requester_id=requester.id, created_by_id=requester.id,
                            school_id=school_id, members=[ChatMember(user_id=requester.id)])
    db.add(conv)
    await db.commit()
    await post_message(db, conv, requester, body)
    if not support_open_now():
        await convert_to_ticket(db, conv, None, reason="closed")
        return conv
    await post_message(db, conv, None, "Pedido recebido. Um técnico vai responder dentro de momentos.", system=True)
    await notify_queue(db)
    agents = await available_agents(db) or {u.id for u in await responders(db)}
    await _push_offline(agents, "Apoio ao vivo", f"{short_name(requester.display_name)}: {body}", "/chat?tab=apoio")
    return conv


async def accept_support(db: AsyncSession, conv: ChatConversation, agent: User) -> None:
    if conv.support_status != "waiting":
        return
    conv.support_status = "active"
    conv.agent_id = agent.id
    if agent.id not in {m.user_id for m in conv.members}:
        conv.members.append(ChatMember(user_id=agent.id))
    await db.commit()
    await post_message(db, conv, None, f"{short_name(agent.display_name)} está a responder.", system=True)
    await notify_queue(db)


async def close_support(db: AsyncSession, conv: ChatConversation, by: User) -> None:
    if conv.support_status not in ("waiting", "active"):
        return
    conv.support_status = "closed"
    await db.commit()
    await post_message(db, conv, None, f"Conversa terminada por {short_name(by.display_name)}.", system=True)
    await notify_queue(db)


async def convert_to_ticket(db: AsyncSession, conv: ChatConversation, by: User | None, reason: str = "manual",
                            title: str | None = None, category_id: int | None = None) -> Ticket | None:
    from app.schemas.ticket import TicketCreate
    from app.services import email_service, ticket_service
    from app.services.realtime_hooks import notify_ticket_lists
    if conv.ticket_id or conv.kind != "support":
        return None
    requester = await db.get(User, conv.requester_id)
    msgs = (await db.execute(select(ChatMessage).where(ChatMessage.conversation_id == conv.id).order_by(ChatMessage.id))).scalars().all()
    lines = []
    for m in msgs:
        if m.is_system:
            continue
        when = m.created_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(_LISBON).strftime("%d/%m %H:%M")
        lines.append(f"[{when}] {short_name(m.author.display_name) if m.author else 'Sistema'}: {m.body}")
    first = next((m.body for m in msgs if not m.is_system and m.author_id == conv.requester_id), "Pedido de apoio")
    intro = {
        "closed": "Pedido enviado pelo apoio ao vivo fora do horário de atendimento.",
        "timeout": "Pedido enviado pelo apoio ao vivo sem resposta a tempo.",
    }.get(reason, "Conversa do apoio ao vivo convertida em ticket.")
    if category_id is None:
        cats = (await db.execute(select(Category).order_by(Category.id))).scalars().all()
        category_id = next((c.id for c in cats if c.name.lower().startswith("outro")), cats[0].id if cats else None)
    # model_construct: a ticket coming from the chat may have no school
    data = TicketCreate.model_construct(
        title=(title or f"Apoio ao vivo: {first}")[:200], description=intro + "\n\n" + "\n".join(lines),
        category_id=category_id, school_id=conv.school_id,
    )
    ticket = await ticket_service.create_ticket(db, data, requester)
    if conv.agent_id:
        agent = await db.get(User, conv.agent_id)
        if agent and "tickets.manage" in permissions_for(agent) and agent not in ticket.assignees:
            ticket.assignees.append(agent)
            ticket.assignee_id = ticket.assignee_id or agent.id
    conv.ticket_id = ticket.id
    conv.support_status = "converted"
    await db.commit()
    text = {
        "closed": f"O apoio ao vivo está fechado neste momento ({support_hours_text()}). Criámos o ticket T-{ticket.id} com a sua mensagem — vai ser respondido por lá.",
        "timeout": f"Nenhum técnico conseguiu responder a tempo. Criámos o ticket T-{ticket.id} com a sua mensagem — vai ser respondido por lá.",
    }.get(reason, f"{short_name(by.display_name) if by else 'A equipa'} converteu esta conversa no ticket T-{ticket.id}.")
    await post_message(db, conv, None, text, system=True)
    if requester and requester.email and ticket.creator_email_notifications:
        await email_service.send_ticket_notification(requester.email, "created", {
            "id": ticket.id, "title": ticket.title, "description": ticket.description,
            "category": ticket.category.name if ticket.category else "", "priority": ticket.priority.value, "school": "",
        })
    await notify_queue(db)
    await notify_ticket_lists()
    return ticket


async def expire_waiting(db: AsyncSession) -> None:
    """Waiting support chats nobody accepted in time become tickets."""
    limit = datetime.utcnow() - timedelta(minutes=support_settings()["wait_minutes"])
    rows = (
        await db.execute(select(ChatConversation).where(
            ChatConversation.kind == "support", ChatConversation.support_status == "waiting", ChatConversation.created_at < limit,
        ))
    ).scalars().all()
    for conv in rows:
        await convert_to_ticket(db, conv, None, reason="timeout")
