"""Read/unread state of tickets per user, like an email inbox.

A ticket is unread for a user when someone else wrote something they can see (reply, internal note for staff,
private message to them) after they last opened it, or when it is a new ticket from someone else that they never
opened. Only activity after the feature was installed counts, so existing tickets don't all show up as unread.
"""
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ticket import Comment, TicketReminder, TicketView
from app.models.user import User
from app.services.permissions import has_perm


def _tracking_since() -> datetime:
    from app.api.v1.settings import _read_settings
    raw = _read_settings().get("unread_tracking_since")
    try:
        return datetime.fromisoformat(raw) if raw else datetime.utcnow()
    except ValueError:
        return datetime.utcnow()


async def mark_read(db: AsyncSession, user_id: int, ticket_ids: list[int]) -> None:
    if not ticket_ids:
        return
    now = datetime.utcnow()
    stmt = insert(TicketView).values([{"user_id": user_id, "ticket_id": tid, "last_read_at": now, "marked_unread": False} for tid in ticket_ids])
    stmt = stmt.on_conflict_do_update(index_elements=["user_id", "ticket_id"], set_={"last_read_at": now, "marked_unread": False})
    await db.execute(stmt)
    await db.commit()


async def mark_unread(db: AsyncSession, user_id: int, ticket_id: int) -> None:
    stmt = insert(TicketView).values(user_id=user_id, ticket_id=ticket_id, last_read_at=None, marked_unread=True)
    stmt = stmt.on_conflict_do_update(index_elements=["user_id", "ticket_id"], set_={"marked_unread": True})
    await db.execute(stmt)
    await db.commit()


async def unread_ids(db: AsyncSession, user: User, tickets) -> set[int]:
    if not tickets:
        return set()
    ids = [t.id for t in tickets]
    since = _tracking_since()
    views = {
        v.ticket_id: v
        for v in (await db.execute(select(TicketView).where(TicketView.user_id == user.id, TicketView.ticket_id.in_(ids)))).scalars()
    }
    # Latest thing written by someone else that this user is allowed to see
    q = select(Comment.ticket_id, func.max(Comment.created_at)).where(
        Comment.ticket_id.in_(ids), Comment.author_id != user.id, Comment.deleted_at.is_(None),
        (Comment.private_to_id.is_(None)) | (Comment.private_to_id == user.id),
    )
    if not has_perm(user, "tickets.manage"):
        q = q.where(Comment.is_internal.is_(False))
    latest = dict((await db.execute(q.group_by(Comment.ticket_id))).all())

    unread: set[int] = set()
    for t in tickets:
        view = views.get(t.id)
        if view and view.marked_unread:
            unread.add(t.id)
            continue
        last_read = view.last_read_at if view else None
        activity = latest.get(t.id)
        if activity and activity > since and (last_read is None or activity > last_read):
            unread.add(t.id)
        elif not view and t.creator_id != user.id and t.created_at and t.created_at > since:
            unread.add(t.id)
    return unread


async def pending_reminders(db: AsyncSession, user: User, ticket_ids: list[int]) -> dict[int, datetime]:
    """Earliest reminder the user set on each ticket that has not been sent yet (reminders are private)."""
    if not ticket_ids:
        return {}
    rows = await db.execute(
        select(Comment.ticket_id, func.min(Comment.remind_at)).where(
            Comment.ticket_id.in_(ticket_ids), Comment.author_id == user.id, Comment.remind_at.is_not(None),
            Comment.reminder_sent_at.is_(None), Comment.deleted_at.is_(None),
        ).group_by(Comment.ticket_id)
    )
    earliest = dict(rows.all())
    standalone = await db.execute(
        select(TicketReminder.ticket_id, func.min(TicketReminder.remind_at)).where(
            TicketReminder.ticket_id.in_(ticket_ids), TicketReminder.user_id == user.id, TicketReminder.sent_at.is_(None),
        ).group_by(TicketReminder.ticket_id)
    )
    for tid, at in standalone.all():
        if tid not in earliest or at < earliest[tid]:
            earliest[tid] = at
    return earliest
