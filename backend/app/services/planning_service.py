"""Planned maintenance: create the tickets of ScheduledTicket entries whose date has come."""
from __future__ import annotations

import calendar
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planning import ScheduledTicket
from app.models.ticket import TicketPriority
from app.models.user import User

logger = logging.getLogger(__name__)
_LISBON = ZoneInfo("Europe/Lisbon")
FREQUENCIES = {"weekly": "Todas as semanas", "monthly": "Todos os meses", "quarterly": "De 3 em 3 meses", "yearly": "Todos os anos"}


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def next_date(d: date, frequency: str) -> date:
    if frequency == "weekly":
        from datetime import timedelta
        return d + timedelta(days=7)
    return _add_months(d, {"monthly": 1, "quarterly": 3, "yearly": 12}.get(frequency, 1))


async def create_ticket_now(db: AsyncSession, plan: ScheduledTicket, actor: User | None = None):
    """Create this plan's ticket (as the person who planned it) and tell whoever is assigned."""
    from app.schemas.ticket import TicketCreate
    from app.services import notifications, ticket_service
    creator = actor or await db.get(User, plan.created_by_id)
    if creator is None or not creator.is_active or plan.school_id is None:
        raise ValueError("Falta a escola ou a pessoa que criou esta manutenção.")
    data = TicketCreate(
        title=plan.title, description=plan.description or plan.title, category_id=plan.category_id,
        school_id=plan.school_id, priority=TicketPriority(plan.priority),
        assignee_ids=[plan.assignee_id] if plan.assignee_id else [], creator_email_notifications=False,
    )
    ticket = await ticket_service.create_ticket(db, data, creator, allow_assignment=True)
    from app.models.ticket import TicketEvent
    db.add(TicketEvent(ticket_id=ticket.id, event_type="scheduled", message="Criado automaticamente pela manutenção planeada"))
    plan.last_ticket_id = ticket.id
    plan.last_run_at = datetime.utcnow()
    await db.commit()
    assigned = list(ticket.assignees or ([ticket.assignee] if ticket.assignee else []))
    if assigned:
        await notifications.notify_assigned(ticket, assigned, None)
    return ticket


async def run_due(db: AsyncSession) -> int:
    today = datetime.now(_LISBON).date()
    plans = (await db.execute(
        select(ScheduledTicket).where(ScheduledTicket.active.is_(True), ScheduledTicket.next_run <= today)
    )).scalars().all()
    created = 0
    for plan in plans:
        try:
            await create_ticket_now(db, plan)
            created += 1
        except Exception:
            await db.rollback()
            logger.exception("Manutenção planeada %s: não foi possível criar o ticket", plan.id)
        # Move on to the next date even if it failed, so a broken entry does not retry every hour
        nxt = plan.next_run
        while nxt <= today:
            nxt = next_date(nxt, plan.frequency)
        plan.next_run = nxt
        await db.commit()
    return created
