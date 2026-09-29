"""Private reminders attached to internal notes: on the chosen date the note's author gets an email and a push."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Comment, Ticket, TicketReminder
from app.services import email_service, push_service
from app.services.notification_prefs import wants

logger = logging.getLogger(__name__)


async def send_due_reminders(db: AsyncSession) -> int:
    """Send every due reminder. Each one is handled on its own: one bad reminder (e.g. its ticket was deleted) no
    longer stops all the others, and each is marked as sent before it goes out, so it is never sent twice."""
    now = datetime.utcnow()
    sent = 0
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
        await db.commit()
        ticket, author = comment.ticket, comment.author
        if ticket is None or author is None:
            logger.warning("Lembrete da nota %s ignorado: ticket ou autor já não existe", comment.id)
            continue
        try:
            if author.email and wants(author, "reminders", "email"):
                await email_service.send_reminder(author.email, {
                    "id": ticket.id,
                    "title": ticket.title,
                    "status": ticket.status.value,
                    "note": comment.body,
                    "note_is_internal": comment.is_internal,
                    "note_is_private": bool(comment.private_to_id),
                    "note_created_at": comment.created_at,
                })
            if wants(author, "reminders", "push"):
                await push_service.send_push_to_users_bg(
                {author.id},
                f"Lembrete · Ticket #{ticket.id}",
                comment.body[:140],
                f"/tickets/{ticket.id}",
            )
            sent += 1
            logger.info("Reminder sent for comment %s (ticket #%s) to %s", comment.id, ticket.id, author.email)
        except Exception:
            logger.exception("Envio do lembrete da nota %s falhou", comment.id)

    # Reminders set on their own ("Lembrar-me deste ticket"), not tied to a reply
    standalone = (await db.execute(
        select(TicketReminder)
        .where(TicketReminder.remind_at <= now, TicketReminder.sent_at.is_(None))
        .options(selectinload(TicketReminder.user), selectinload(TicketReminder.ticket).selectinload(Ticket.category))
    )).scalars().all()
    for reminder in standalone:
        reminder.sent_at = now
        await db.commit()
        ticket, user = reminder.ticket, reminder.user
        if ticket is None or user is None:
            logger.warning("Lembrete %s ignorado: ticket ou utilizador já não existe", reminder.id)
            continue
        try:
            if user.email and wants(user, "reminders", "email"):
                await email_service.send_reminder(user.email, {
                    "id": ticket.id,
                    "title": ticket.title,
                    "status": ticket.status.value,
                    "note": reminder.note or "",
                    "note_is_reminder": True,
                    "note_created_at": reminder.created_at,
                })
            if wants(user, "reminders", "push"):
                await push_service.send_push_to_users_bg(
                {user.id}, f"Lembrete · Ticket #{ticket.id}", (reminder.note or ticket.title)[:140], f"/tickets/{ticket.id}",
            )
            sent += 1
            logger.info("Reminder %s sent (ticket #%s) to %s", reminder.id, ticket.id, user.email)
        except Exception:
            logger.exception("Envio do lembrete %s falhou", reminder.id)

    return sent
