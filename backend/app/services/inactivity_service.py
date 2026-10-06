"""
Inactivity auto-warning and auto-close service.

Logic (per active, non-archived ticket):
  0. If the requester spoke last (or nobody from the team has answered yet), the ticket is waiting for the team:
     it is never closed. After 7 days without activity the team is asked, by email, for a status update and the
     requester is told the ticket is being followed up — again every 7 days while nothing happens.
  1. If updated_at < now-7d AND no warning event sent after updated_at  → send warning
  2. If latest warning event > updated_at AND warning.created_at < now-2d → close ticket

Using updated_at as the activity signal is safe because ticket_service always
sets ticket.updated_at when a comment is added, status changes, etc.
The warning TicketEvent does NOT update ticket.updated_at, so the signal stays clean.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.group import HelpdeskGroup
from app.models.ticket import Comment, Ticket, TicketEvent, TicketStatus, comment_private_recipients
from app.models.user import User, UserRole
from app.services import email_service

logger = logging.getLogger(__name__)

_WARN_DAYS = 7
_CLOSE_DAYS = 2
_ACTIVE = frozenset({
    TicketStatus.OPEN,
    TicketStatus.ASSIGNED,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_USER,
})


async def run_inactivity_check(db: AsyncSession) -> dict:
    now = datetime.utcnow()
    warn_cutoff = now - timedelta(days=_WARN_DAYS)
    close_cutoff = now - timedelta(days=_CLOSE_DAYS)

    warned = 0
    closed = 0
    status_requests = 0

    tickets = (await db.execute(
        select(Ticket)
        .where(Ticket.status.in_(list(_ACTIVE)))
        .where(Ticket.archived_at.is_(None))
        .options(
            selectinload(Ticket.creator),
            selectinload(Ticket.assignee),
            selectinload(Ticket.assignees),
            selectinload(Ticket.watchers),
            selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
        )
    )).scalars().all()

    for ticket in tickets:
        last_public = await _last_public_comment(db, ticket.id)
        if last_public is None or not _is_team(last_public.author):
            # Waiting for the team, not for the requester: never close, ask the team where things stand
            if ticket.updated_at < warn_cutoff and await _status_request_due(db, ticket.id, warn_cutoff):
                days = (now - ticket.updated_at).days
                db.add(TicketEvent(
                    ticket_id=ticket.id,
                    actor_id=None,
                    event_type="status_request",
                    message=f"Sem resposta da equipa há {days} dias: pedido o ponto de situação por email.",
                ))
                status_requests += 1
                await _ask_team_for_status(db, ticket, last_public, days)
            continue

        latest_warning = (await db.execute(
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket.id)
            .where(TicketEvent.event_type == "inactivity_warning")
            .order_by(TicketEvent.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        warning_is_fresh = (
            latest_warning is not None
            and latest_warning.created_at > ticket.updated_at
        )

        if warning_is_fresh:
            # Warning already sent for this inactivity period
            if latest_warning.created_at < close_cutoff:
                # 2+ days since warning with no activity → close
                ticket.status = TicketStatus.CLOSED
                ticket.updated_at = now
                ticket.closed_via_email = False
                db.add(TicketEvent(
                    ticket_id=ticket.id,
                    actor_id=None,
                    event_type="status_changed",
                    message="Ticket fechado automaticamente por inatividade (sem resposta após aviso de 2 dias).",
                ))
                closed += 1
                await _notify(
                    ticket,
                    "O seu ticket foi fechado automaticamente por falta de resposta. "
                    "Se necessitar de mais assistência, abra um novo ticket.",
                    closing=True,
                )
        else:
            # No fresh warning — check if ticket has been inactive long enough
            if ticket.updated_at < warn_cutoff:
                close_on = (now + timedelta(days=_CLOSE_DAYS)).strftime("%d/%m/%Y")
                msg = (
                    f"Este ticket está sem atividade há {_WARN_DAYS} dias. "
                    f"Se não houver resposta até {close_on}, será fechado automaticamente."
                )
                db.add(TicketEvent(
                    ticket_id=ticket.id,
                    actor_id=None,
                    event_type="inactivity_warning",
                    message=msg,
                ))
                warned += 1
                await _notify(ticket, msg, closing=False)

    await db.commit()
    logger.info("Inactivity check: %d warned, %d closed, %d status requests", warned, closed, status_requests)
    return {"warned": warned, "closed": closed, "status_requests": status_requests}


def _is_team(user: User | None) -> bool:
    return user is not None and (user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or bool(user.is_technician))


async def _last_public_comment(db: AsyncSession, ticket_id: int) -> Comment | None:
    """Last reply everyone on the ticket can see (no internal notes, private messages or deleted replies)."""
    is_private = exists().where(comment_private_recipients.c.comment_id == Comment.id)
    return (await db.execute(
        select(Comment)
        .where(Comment.ticket_id == ticket_id)
        .where(Comment.is_internal.is_(False))
        .where(Comment.deleted_at.is_(None))
        .where(Comment.private_to_id.is_(None))
        .where(~is_private)
        .options(selectinload(Comment.author))
        .order_by(Comment.created_at.desc(), Comment.id.desc())
        .limit(1)
    )).scalar_one_or_none()


async def _status_request_due(db: AsyncSession, ticket_id: int, cutoff: datetime) -> bool:
    last = (await db.execute(
        select(TicketEvent.created_at)
        .where(TicketEvent.ticket_id == ticket_id)
        .where(TicketEvent.event_type == "status_request")
        .order_by(TicketEvent.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    return last is None or last < cutoff


async def _ask_team_for_status(db: AsyncSession, ticket: Ticket, last_public: Comment | None, days: int) -> None:
    team: dict[int, User] = {}
    for u in [ticket.assignee, *getattr(ticket, "assignees", [])]:
        if u is not None:
            team[u.id] = u
    if ticket.group:
        for m in ticket.group.members:
            team[m.id] = m
    if not team:
        # Nobody responsible yet: the whole support team
        for u in (await db.execute(
            select(User).where(User.is_active.is_(True)).where(
                (User.role.in_([UserRole.ADMIN, UserRole.TECHNICIAN])) | (User.is_technician.is_(True))
            )
        )).scalars():
            team[u.id] = u
    team.pop(ticket.creator_id, None)

    if last_public is not None:
        body, at = last_public.body or "", last_public.created_at
    else:
        body, at = ticket.description or "", ticket.created_at
    if len(body) > 1500:
        body = body[:1500] + "…"
    data = {
        "id": ticket.id,
        "title": ticket.title,
        "status": ticket.status.value,
        "days": days,
        "requester": ticket.creator.display_name if ticket.creator else "",
        "last_message": body.strip(),
        "last_message_at": at.strftime("%d/%m/%Y") if at else "",
    }
    for u in team.values():
        if not u.email or not u.is_active:
            continue
        try:
            await email_service.send_ticket_email_now(u.email, "status_request", data)
        except Exception:
            logger.exception("Inactivity: failed to ask %s for a status update on ticket #%d", u.email, ticket.id)

    # The requester learns the request has not been forgotten
    creator = ticket.creator
    if creator and creator.email and ticket.creator_email_notifications and not _is_team(creator):
        try:
            await email_service.send_ticket_email_now(creator.email, "status_followup", data)
        except Exception:
            logger.exception("Inactivity: failed to tell %s that ticket #%d is being followed up", creator.email, ticket.id)


async def _notify(ticket: Ticket, message: str, *, closing: bool) -> None:
    recipients: set[str] = set()
    if ticket.creator_email_notifications and ticket.creator.email:
        recipients.add(ticket.creator.email)
    if ticket.assignee and ticket.assignee.email:
        recipients.add(ticket.assignee.email)
    for a in getattr(ticket, "assignees", []):
        if a.email:
            recipients.add(a.email)
    for w in ticket.watchers:
        if w.email:
            recipients.add(w.email)
    if ticket.group:
        for m in ticket.group.members:
            if m.email:
                recipients.add(m.email)

    event_type = "closed" if closing else "updated"
    for r in recipients:
        try:
            await email_service.send_ticket_notification(
                r, event_type,
                {"id": ticket.id, "title": ticket.title, "status": ticket.status.value, "message": message},
            )
        except Exception:
            logger.exception("Inactivity: failed to notify %s for ticket #%d", r, ticket.id)
