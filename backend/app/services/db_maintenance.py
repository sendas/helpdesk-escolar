"""SQLite housekeeping: consistent snapshots, orphan clean-up and removing tickets with everything that hangs off them."""
from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import sqlite_path

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/app/data/uploads")
SNAPSHOT_DIR = Path("/app/data/snapshots")
STARTUP_SNAPSHOTS_KEPT = 5


def snapshot_to(dest: str | Path) -> Path | None:
    """Copy the live database to `dest` with SQLite's backup API: a consistent copy even while the app is writing
    (a plain file copy can be torn, and in WAL mode misses what is still in the -wal file)."""
    src_path = sqlite_path()
    if not src_path or not os.path.exists(src_path):
        return None
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.unlink(missing_ok=True)
    src = sqlite3.connect(src_path, timeout=30)
    try:
        out = sqlite3.connect(tmp)
        try:
            src.backup(out)
            # A standalone file: no -wal/-shm companions needed to read it
            out.execute("PRAGMA journal_mode=DELETE")
        finally:
            out.close()
    finally:
        src.close()
    os.replace(tmp, dest)
    return dest


def startup_snapshot() -> Path | None:
    """Keep a copy of the database as it was before this version started (and ran its migrations)."""
    try:
        path = snapshot_to(SNAPSHOT_DIR / f"tickets-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
        old = sorted(SNAPSHOT_DIR.glob("tickets-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for extra in old[STARTUP_SNAPSHOTS_KEPT:]:
            extra.unlink(missing_ok=True)
        if path:
            logger.info("Cópia da base de dados antes do arranque: %s", path)
        return path
    except Exception:
        logger.exception("Não foi possível criar a cópia de segurança de arranque")
        return None


# Rows whose parent ticket/comment is gone. Deleting a ticket used to leave these behind, and a reminder pointing
# at a deleted ticket stopped every reminder from being sent.
_ORPHAN_DELETES = (
    "DELETE FROM ticket_reminders WHERE ticket_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM ticket_views WHERE ticket_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM ticket_watchers WHERE ticket_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM ticket_assignees WHERE ticket_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM processed_emails WHERE ticket_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM ticket_events WHERE ticket_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM comments WHERE ticket_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM reactions WHERE target_type = 'comment' AND target_id NOT IN (SELECT id FROM comments)",
    "DELETE FROM reactions WHERE target_type = 'ticket' AND target_id NOT IN (SELECT id FROM tickets)",
    "DELETE FROM reactions WHERE target_type = 'chat' AND target_id NOT IN (SELECT id FROM chat_messages)",
    "UPDATE chat_conversations SET ticket_id = NULL WHERE ticket_id IS NOT NULL AND ticket_id NOT IN (SELECT id FROM tickets)",
    "UPDATE tickets SET group_id = NULL WHERE group_id IS NOT NULL AND group_id NOT IN (SELECT id FROM helpdesk_groups)",
    "UPDATE tickets SET school_id = NULL WHERE school_id IS NOT NULL AND school_id NOT IN (SELECT id FROM schools)",
    "UPDATE ticket_routing_rules SET group_id = NULL WHERE group_id IS NOT NULL AND group_id NOT IN (SELECT id FROM helpdesk_groups)",
    "UPDATE ticket_routing_rules SET school_id = NULL WHERE school_id IS NOT NULL AND school_id NOT IN (SELECT id FROM schools)",
    "UPDATE ticket_routing_rules SET category_id = NULL WHERE category_id IS NOT NULL AND category_id NOT IN (SELECT id FROM categories)",
    "UPDATE knowledge_articles SET category_id = NULL WHERE category_id IS NOT NULL AND category_id NOT IN (SELECT id FROM categories)",
)


async def cleanup_orphans(conn) -> None:
    total = 0
    for sql in _ORPHAN_DELETES:
        try:
            result = await conn.execute(text(sql))
            total += max(result.rowcount or 0, 0)
        except Exception:
            logger.exception("Limpeza de registos órfãos falhou: %s", sql)
    if total:
        logger.warning("Limpeza da base de dados: %s registos sem ticket/categoria/grupo foram corrigidos", total)
    # Attachment rows of deleted tickets: remove the files too
    rows = (await conn.execute(text("SELECT stored_name FROM attachments WHERE ticket_id NOT IN (SELECT id FROM tickets)"))).all()
    if rows:
        await conn.execute(text("DELETE FROM attachments WHERE ticket_id NOT IN (SELECT id FROM tickets)"))
        remove_upload_files([r[0] for r in rows])


def remove_upload_files(names: list[str]) -> None:
    for name in names:
        if not name or "/" in name or "\\" in name or name.startswith("."):
            continue
        try:
            (UPLOAD_DIR / name).unlink(missing_ok=True)
        except OSError:
            logger.warning("Não foi possível apagar o anexo %s", name)


async def purge_tickets(db: AsyncSession, ids: list[int]) -> list[str]:
    """Delete tickets and every row that belongs to them. Returns the stored attachment file names, to be removed
    from disk once the transaction has been committed."""
    from app.models.chat import ChatConversation
    from app.models.reaction import Reaction
    from app.models.ticket import (
        Attachment, Comment, ProcessedEmail, Ticket, TicketEvent, TicketReminder, TicketView,
        ticket_assignees, ticket_watchers,
    )

    if not ids:
        return []
    files = list((await db.execute(select(Attachment.stored_name).where(Attachment.ticket_id.in_(ids)))).scalars())
    comment_ids = select(Comment.id).where(Comment.ticket_id.in_(ids))
    await db.execute(delete(Reaction).where(Reaction.target_type == "comment", Reaction.target_id.in_(comment_ids)))
    await db.execute(delete(Reaction).where(Reaction.target_type == "ticket", Reaction.target_id.in_(ids)))
    await db.execute(update(ChatConversation).where(ChatConversation.ticket_id.in_(ids)).values(ticket_id=None))
    for model in (TicketReminder, TicketView, ProcessedEmail, TicketEvent, Attachment, Comment):
        await db.execute(delete(model).where(model.ticket_id.in_(ids)))
    for table in (ticket_assignees, ticket_watchers):
        await db.execute(delete(table).where(table.c.ticket_id.in_(ids)))
    await db.execute(delete(Ticket).where(Ticket.id.in_(ids)))
    return files


# What still points at a category/school/group about to be deleted. Optional links are cleared; with foreign keys
# enforced the delete would otherwise fail.
_DETACH = {
    "categories": (
        "UPDATE ticket_routing_rules SET category_id = NULL WHERE category_id = :id",
        "UPDATE knowledge_articles SET category_id = NULL WHERE category_id = :id",
    ),
    "schools": (
        "UPDATE tickets SET school_id = NULL WHERE school_id = :id",
        "UPDATE ticket_routing_rules SET school_id = NULL WHERE school_id = :id",
        "UPDATE chat_conversations SET school_id = NULL WHERE school_id = :id",
    ),
    "helpdesk_groups": (
        "UPDATE tickets SET group_id = NULL WHERE group_id = :id",
        "UPDATE ticket_routing_rules SET group_id = NULL WHERE group_id = :id",
    ),
}


async def detach(db: AsyncSession, table: str, row_id: int) -> None:
    for sql in _DETACH[table]:
        await db.execute(text(sql), {"id": row_id})


async def category_ticket_count(db: AsyncSession, category_id: int) -> int:
    return (await db.execute(text("SELECT COUNT(*) FROM tickets WHERE category_id = :id"), {"id": category_id})).scalar_one()
