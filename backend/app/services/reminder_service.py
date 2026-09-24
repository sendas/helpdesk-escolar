"""Private reminders attached to internal notes: on the chosen date the note's author gets an email and a push."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Comment, Ticket
from app.services import email_service, push_service

logger = logging.getLogger(__name__)


async def send_due_reminders(db: AsyncSession) -> int:
    now = datetime.utcnow()
    due = (await db.execute(
        select(Comment)
        .where(
            Comment.remind_at.is_not(None),
            Comment.remind_at <= now,
            Comment.reminder_sent_at.is_(None),
            Comment.deleted_at.is_(None),
        )
        .options(selectinload(Comment.author), selectinload(Comment.ticket).selectinload(Ticket.category))
    )).scalars().all()

    for comment in due:
        comment.reminder_sent_at = now
        ticket, author = comment.ticket, comment.author
        if author and author.email:
            await email_service.send_reminder(author.email, {
                "id": ticket.id,
                "title": ticket.title,
                "status": ticket.status.value,
                "note": comment.body,
                "note_created_at": comment.created_at,
            })
        if author:
            await push_service.send_push_to_users_bg(
                {author.id},
                f"Lembrete · Ticket #{ticket.id}",
                comment.body[:140],
                f"/tickets/{ticket.id}",
            )
        logger.info("Reminder sent for comment %s (ticket #%s) to %s", comment.id, ticket.id, author.email if author else "?")

    if due:
        await db.commit()
    return len(due)
