"""Who is told what when a ticket changes (email and push), in one place.

Rules:
- Nobody is told about their own action.
- Replies: requester, assignees, group, followers and the category's address, as each person prefers.
- State changes: only the requester (and followers who are not in the support team) and only when it concerns them:
  waiting for their answer, resolved or closed. Staff get them only if they turned them on in their preferences.
- Priority/group changes: no email; only a person who becomes responsible is told ("assigned").
- Support company (ticket reported to it): replies and the closing, each time with the conversation so far.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timezone
from zoneinfo import ZoneInfo

from app.models.ticket import Ticket, TicketStatus
from app.models.user import User
from app.services import email_service, push_service
from app.services.notification_prefs import wants

logger = logging.getLogger(__name__)

REQUESTER_STATES = {TicketStatus.WAITING_USER, TicketStatus.RESOLVED, TicketStatus.CLOSED}
DONE_STATES = {TicketStatus.RESOLVED, TicketStatus.CLOSED}
_LISBON = ZoneInfo("Europe/Lisbon")
_STATUS_PT = {
    "open": "Aberto", "assigned": "Atribuído", "in_progress": "Em Curso", "waiting_user": "A aguardar utilizador",
    "resolved": "Resolvido", "closed": "Fechado",
}


def _people(ticket: Ticket) -> dict[int, User]:
    people: dict[int, User] = {}
    for u in [ticket.creator, ticket.assignee, *getattr(ticket, "assignees", []), *getattr(ticket, "watchers", []),
              *((ticket.group.members if ticket.group else []))]:
        if u is not None and u.is_active:
            people.setdefault(u.id, u)
    return people


def _is_staff(user: User) -> bool:
    from app.models.user import UserRole
    return user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or bool(user.is_technician)


def _requester_ok(ticket: Ticket, user: User) -> bool:
    """The requester can switch off emails for one ticket ("Atualizações por email")."""
    return user.id != ticket.creator_id or bool(ticket.creator_email_notifications)


def _push(users: list[User], kind: str, title: str, body: str, url: str) -> None:
    ids = {u.id for u in users if wants(u, kind, "push")}
    if ids:
        asyncio.create_task(push_service.send_push_to_users_bg(ids, title, body, url))


def _provider() -> tuple[str, str]:
    from app.api.v1.settings import _read_settings
    s = _read_settings()
    return (s.get("support_provider_email") or "").strip(), (s.get("support_provider_name") or "Empresa de apoio").strip()


def _when(dt) -> str:
    return dt.replace(tzinfo=timezone.utc).astimezone(_LISBON).strftime("%d/%m/%Y %H:%M") if dt else ""


def conversation(ticket: Ticket, exclude_comment_id: int | None = None, limit: int = 30) -> list[dict]:
    """The public conversation for the support company: never internal notes or private messages."""
    rows = [
        c for c in sorted(getattr(ticket, "comments", []), key=lambda c: c.created_at)
        if c.deleted_at is None and not c.is_internal and not c.private_to_id and c.id != exclude_comment_id
    ]
    return [
        {"author": c.author.display_name if c.author else "?", "when": _when(c.created_at), "body": c.body}
        for c in rows[-limit:]
    ]


def attachment_names(ticket: Ticket) -> list[str]:
    return [a.original_name for a in getattr(ticket, "attachments", [])]


async def send_to_provider(ticket: Ticket, event: str, extra: dict, exclude_comment_id: int | None = None) -> bool:
    email, name = _provider()
    from app.config import settings
    if not email or not settings.mail_server:
        return False
    data = {
        "id": ticket.id, "title": ticket.title, "provider": name,
        "status": ticket.status.value, "priority": ticket.priority.value,
        "description": ticket.description,
        "requester": ticket.creator.display_name if ticket.creator else "",
        "requester_email": ticket.creator.email if ticket.creator else "",
        "category": ticket.category.name if ticket.category else "",
        "school": ticket.school.name if ticket.school else "",
        "conversation": conversation(ticket, exclude_comment_id),
        "attachments": attachment_names(ticket),
        **extra,
    }
    await email_service.send_ticket_email_now(email, event, data)
    return True


async def notify_reply(ticket: Ticket, actor: User, body: str, new_status: TicketStatus | None = None,
                       comment_id: int | None = None) -> None:
    """A public reply (optionally with a new state, in the same email)."""
    payload = {"id": ticket.id, "title": ticket.title, "author": actor.display_name, "comment": body}
    if new_status is not None:
        payload["new_status"] = _STATUS_PT.get(new_status.value, new_status.value)
    targets = [u for u in _people(ticket).values() if u.id != actor.id and _requester_ok(ticket, u)]
    sent: set[str] = set()
    for u in targets:
        if u.email and wants(u, "replies", "email"):
            await email_service.send_ticket_notification(u.email, "commented", payload)
            sent.add(u.email.lower())
    category_email = (ticket.category.email_to or "").strip() if ticket.category else ""
    if category_email and category_email.lower() not in sent and category_email.lower() != (actor.email or "").lower():
        await email_service.send_ticket_notification(category_email, "commented", payload)
    _push(targets, "replies", f"Nova resposta: {ticket.title}", f"{actor.display_name}: {body[:80]}", f"/tickets/{ticket.id}")
    if ticket.is_escalated:
        await send_to_provider(ticket, "supplier_comment", {"author": actor.display_name, "comment": body}, exclude_comment_id=comment_id)


async def notify_status(ticket: Ticket, actor: User | None, old: TicketStatus | None, new: TicketStatus,
                        bulk: bool = False) -> None:
    if old == new:
        return
    wanted_states = DONE_STATES if bulk else REQUESTER_STATES
    label = _STATUS_PT.get(new.value, new.value)
    payload = {"id": ticket.id, "title": ticket.title, "status": new.value}
    email_to: list[User] = []
    push_to: list[User] = []
    for u in _people(ticket).values():
        if actor is not None and u.id == actor.id:
            continue
        # Requester and followers from outside the team: only the states that concern them. Team: if they asked for it
        concerns = new in wanted_states if (u.id == ticket.creator_id or not _is_staff(u)) else not bulk
        if not concerns or not _requester_ok(ticket, u):
            continue
        if u.email and wants(u, "status", "email"):
            email_to.append(u)
        push_to.append(u)
    for u in email_to:
        await email_service.send_ticket_notification(u.email, "updated", payload)
    _push(push_to, "status", f"Ticket {label.lower()}: {ticket.title}", f"Estado: {label}", f"/tickets/{ticket.id}")
    if ticket.is_escalated and new in DONE_STATES:
        await send_to_provider(ticket, "supplier_updated", {"editor": actor.display_name if actor else "Sistema"})


async def notify_assigned(ticket: Ticket, users: list[User], actor: User | None, label: str | None = None) -> None:
    """People who have just become responsible (directly or through a group)."""
    targets = [u for u in users if u and u.is_active and (actor is None or u.id != actor.id)]
    for u in targets:
        if u.email and wants(u, "assigned", "email"):
            await email_service.send_ticket_notification(u.email, "assigned", {
                "id": ticket.id, "title": ticket.title, "assignee": label or u.display_name,
            })
    _push(targets, "assigned", f"Ticket atribuído: {ticket.title}", f"T-{ticket.id} · {ticket.category.name if ticket.category else ''}", f"/tickets/{ticket.id}")


async def notify_mentions(ticket: Ticket, actor: User, people: list[User], body: str, internal: bool = False,
                          private: bool = False) -> None:
    """Someone wrote @Name: tell that person (they already passed the "may read this" check)."""
    kind = "nota interna" if internal else "mensagem privada" if private else "resposta"
    for u in people:
        if u.email and wants(u, "mentions", "email"):
            await email_service.send_ticket_notification(u.email, "mentioned", {
                "id": ticket.id, "title": ticket.title, "author": actor.display_name, "comment": body, "kind": kind,
            })
    _push(people, "mentions", f"{actor.display_name} mencionou-o", f"T-{ticket.id}: {body[:80]}", f"/tickets/{ticket.id}")
