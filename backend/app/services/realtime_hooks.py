"""Glue between database changes and the real-time channel."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.group import HelpdeskGroup
from app.models.ticket import Ticket
from app.models.user import User
from app.services import realtime
from app.services.permissions import permissions_for


async def online_with_perm(db, *perms: str) -> set[int]:
    online = realtime.online_users()
    if not online:
        return set()
    users = (await db.execute(select(User).where(User.id.in_(online)))).scalars().all()
    return {u.id for u in users if permissions_for(u) & set(perms)}


async def notify_ticket(ticket_id: int) -> None:
    """A ticket changed: viewers reload it; everyone linked to it (and supervisors online) refresh lists."""
    try:
        async with AsyncSessionLocal() as db:
            ticket = (
                await db.execute(
                    select(Ticket).where(Ticket.id == ticket_id).options(
                        selectinload(Ticket.assignees), selectinload(Ticket.watchers),
                        selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
                    )
                )
            ).scalar_one_or_none()
            if not ticket:
                return
            related = {ticket.creator_id, ticket.assignee_id, *(a.id for a in ticket.assignees), *(w.id for w in ticket.watchers)}
            if ticket.group:
                related |= {m.id for m in ticket.group.members}
            related |= await online_with_perm(db, "tickets.view_all", "tickets.manage")
        realtime.ticket_changed(ticket_id, related)
    except Exception:
        pass


async def notify_ticket_lists() -> None:
    """Several tickets changed at once (bulk actions, new ticket): refresh lists and counters."""
    try:
        async with AsyncSessionLocal() as db:
            staff = await online_with_perm(db, "tickets.view_all", "tickets.manage")
        realtime.publish(staff, {"type": "tickets.changed"})
    except Exception:
        pass
