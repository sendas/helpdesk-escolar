from __future__ import annotations

import asyncio
import email
import imaplib
import re
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ticket import Comment, ProcessedEmail, Ticket
from app.models.user import User

TICKET_RE = re.compile(r"\[Ticket\s+#(\d+)\]", re.IGNORECASE)


async def sync_inbound_replies(db: AsyncSession, limit: int = 25) -> dict:
    if not settings.mail_reply_enabled or not settings.imap_server:
        return {"processed": 0, "skipped": 0}

    messages = await asyncio.to_thread(_fetch_unseen_messages, limit)
    processed = 0
    skipped = 0

    for msg in messages:
        if not msg["message_id"]:
            skipped += 1
            continue
        exists = await db.execute(select(ProcessedEmail).where(ProcessedEmail.message_id == msg["message_id"]))
        if exists.scalar_one_or_none():
            skipped += 1
            continue

        ticket = (await db.execute(select(Ticket).where(Ticket.id == msg["ticket_id"]))).scalar_one_or_none()
        user = (await db.execute(select(User).where(User.email.ilike(msg["sender_email"])))).scalar_one_or_none()
        if not ticket or not user or not msg["body"]:
            skipped += 1
            continue

        db.add(Comment(body=msg["body"], is_internal=False, ticket_id=ticket.id, author_id=user.id))
        db.add(ProcessedEmail(message_id=msg["message_id"], ticket_id=ticket.id, sender_email=msg["sender_email"]))
        processed += 1

    await db.commit()
    return {"processed": processed, "skipped": skipped}


def _fetch_unseen_messages(limit: int) -> list[dict]:
    username = settings.imap_username or settings.mail_username
    password = settings.imap_password or settings.mail_password
    if not username or not password:
        return []

    client_cls = imaplib.IMAP4_SSL if settings.imap_ssl else imaplib.IMAP4
    client = client_cls(settings.imap_server, settings.imap_port)
    try:
        client.login(username, password)
        client.select(settings.imap_folder)
        status, data = client.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []

        results: list[dict] = []
        ids = data[0].split()[-limit:]
        for msg_id in ids:
            status, fetched = client.fetch(msg_id, "(RFC822)")
            if status != "OK" or not fetched:
                continue
            raw = fetched[0][1]
            parsed = email.message_from_bytes(raw)
            item = _parse_reply(parsed)
            if item:
                results.append(item)
                client.store(msg_id, "+FLAGS", "\\Seen")
        return results
    finally:
        try:
            client.logout()
        except Exception:
            pass


def _parse_reply(msg: Message) -> dict | None:
    subject = _decode_header_value(msg.get("Subject", ""))
    match = TICKET_RE.search(subject)
    if not match:
        return None

    sender_email = parseaddr(msg.get("From", ""))[1].strip().lower()
    body = _clean_reply_body(_extract_text_body(msg))
    return {
        "message_id": (msg.get("Message-ID") or f"{sender_email}:{subject}:{hash(body)}").strip(),
        "ticket_id": int(match.group(1)),
        "sender_email": sender_email,
        "body": body,
    }


def _decode_header_value(value: str) -> str:
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_text_body(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                return _decode_payload(part)
        return ""
    return _decode_payload(msg)


def _decode_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not payload:
        return ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _clean_reply_body(body: str) -> str:
    lines: list[str] = []
    for line in body.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if re.match(r"^(On|Em) .+(wrote|escreveu):$", stripped, flags=re.IGNORECASE):
            break
        if stripped.startswith("-- "):
            break
        lines.append(line.rstrip())
    return "\n".join(lines).strip()[:10000]
