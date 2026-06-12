"""
Inactivity auto-warning and auto-close service.

Logic (per active, non-archived ticket):
  1. If updated_at < now-7d AND no warning event sent after updated_at  → send warning
  2. If latest warning event > updated_at AND warning.created_at < now-2d → close ticket

Using updated_at as the activity signal is safe because ticket_service always
sets ticket.updated_at when a comment is added, status changes, etc.
The warning TicketEvent does NOT update ticket.updated_at, so the signal stays clean.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.group import HelpdeskGroup
from app.models.ticket import Ticket, TicketEvent, TicketStatus
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
    logger.info("Inactivity check: %d warned, %d closed", warned, closed)
    return {"warned": warned, "closed": closed}


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
