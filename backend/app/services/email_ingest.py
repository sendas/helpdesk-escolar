from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import re
from datetime import datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr

import httpx
import msal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.group import HelpdeskGroup
from app.models.ticket import Comment, ProcessedEmail, Ticket, TicketEvent, TicketStatus
from app.models.user import User
from app.services import email_service

TICKET_RE = re.compile(r"\[Ticket\s+#(\d+)\]", re.IGNORECASE)
# Matches "O Seu Ticket de Apoio ao Cliente [Ticket #XX]" in the body
BODY_TICKET_RE = re.compile(r"O\s+Seu\s+Ticket\s+de\s+Apoio\s+ao\s+Cliente\s*[\r\n\s]*\[Ticket\s*#(\d+)\]", re.IGNORECASE)
# Subject keywords that trigger automatic ticket status change
CLOSE_SUBJECT_RE = re.compile(r"\b(FECHADO|resolvido|resolved|closed)\b", re.IGNORECASE)
_SUBJECT_STATUS_MAP: dict[str, str] = {
    "fechado": "closed",
    "closed": "closed",
    "resolvido": "resolved",
    "resolved": "resolved",
}
logger = logging.getLogger(__name__)


async def sync_inbound_replies(db: AsyncSession, limit: int = 25, force: bool = False) -> dict:
    if not settings.mail_reply_enabled:
        logger.info("Mail reply sync disabled: MAIL_REPLY_ENABLED is false")
        return {"processed": 0, "skipped": 0, "provider": _reply_provider()}

    provider = _reply_provider()
    if provider == "graph":
        messages = await _fetch_graph_unread_messages(limit, force=force)
    elif provider == "imap":
        if not settings.imap_server:
            logger.warning("Mail reply sync disabled: IMAP_SERVER is empty")
            return {"processed": 0, "skipped": 0, "provider": provider}
        messages = await asyncio.to_thread(_fetch_unseen_messages, limit, force)
    else:
        logger.warning("Mail reply sync disabled: unsupported MAIL_REPLY_PROVIDER=%s", settings.mail_reply_provider)
        return {"processed": 0, "skipped": 0, "provider": provider}

    logger.info("Mail reply sync fetched %s candidate message(s) via %s (force=%s)", len(messages), provider, force)
    result = await _import_messages(db, messages)
    result["provider"] = provider
    return result


def _reply_provider() -> str:
    return (settings.mail_reply_provider or "imap").strip().lower()


async def _fetch_graph_unread_messages(limit: int, force: bool = False) -> list[dict]:
    mailbox = (settings.graph_mail_user or settings.imap_username or settings.mail_username or settings.mail_from).strip()
    if not mailbox:
        logger.warning("Graph mail reply sync disabled: GRAPH_MAIL_USER/MAIL_USERNAME is empty")
        return []
    if not settings.azure_tenant_id or not settings.azure_client_id or not settings.azure_client_secret:
        logger.warning("Graph mail reply sync disabled: Azure app credentials are incomplete")
        return []

    token = await asyncio.to_thread(_get_graph_token)
    if not token:
        return []

    folder = _graph_folder_id(settings.imap_folder)
    select_fields = "id,subject,from,body,uniqueBody,internetMessageId,isRead"
    params: dict = {
        "$top": str(max(1, min(limit, 200))),
        "$orderby": "receivedDateTime desc",
        "$select": select_fields,
    }
    if not force:
        params["$filter"] = "isRead eq false"
    base_url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/mailFolders/{folder}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": 'outlook.body-content-type="text"',
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(base_url, headers=headers, params=params)
        except Exception:
            logger.exception("Graph mail reply sync failed while fetching messages")
            return []
        if resp.status_code != 200:
            logger.warning("Graph mail reply sync failed: %s %s", resp.status_code, resp.text[:500])
            return []

        data = resp.json()
        raw_messages = data.get("value") or []
        logger.info("Graph mail search found %s unread message(s)", len(raw_messages))

        results: list[dict] = []
        for raw in raw_messages:
            item = _parse_graph_message(raw)
            if item:
                results.append(item)
                await _mark_graph_message_read(client, mailbox, raw["id"], headers)
            else:
                logger.info("Graph mail message ignored: subject does not contain ticket marker")
        return results


def _get_graph_token() -> str | None:
    app = msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        return result["access_token"]
    logger.warning("Graph mail token failed: %s %s", result.get("error"), result.get("error_description"))
    return None


def _graph_folder_id(folder: str) -> str:
    normalized = (folder or "inbox").strip().lower()
    if normalized in {"inbox", "caixa de entrada", "entrada"}:
        return "inbox"
    return folder.strip()


def _parse_graph_message(msg: dict) -> dict | None:
    subject = msg.get("subject") or ""
    sender_email = (
        ((msg.get("from") or {}).get("emailAddress") or {}).get("address") or ""
    ).strip().lower()
    body_info = msg.get("uniqueBody") or msg.get("body") or {}
    body_content = body_info.get("content") or ""
    content_type = (body_info.get("contentType") or "text").lower()
    if content_type == "html":
        body_content = _html_to_text(body_content)

    # Try ticket ID from subject first, then from body pattern
    match = TICKET_RE.search(subject) or BODY_TICKET_RE.search(body_content)
    if not match:
        return None

    status_action = _detect_status_action(subject)
    body = _clean_reply_body(body_content)
    message_id = (msg.get("internetMessageId") or msg.get("id") or f"{sender_email}:{subject}:{hash(body)}").strip()
    return {
        "message_id": message_id,
        "ticket_id": int(match.group(1)),
        "sender_email": sender_email,
        "body": body,
        "status_action": status_action,
    }


async def _mark_graph_message_read(client: httpx.AsyncClient, mailbox: str, message_id: str, headers: dict) -> None:
    try:
        resp = await client.patch(
            f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{message_id}",
            headers={**headers, "Content-Type": "application/json"},
            json={"isRead": True},
        )
        if resp.status_code not in (200, 202):
            logger.warning("Graph mail could not mark message as read: %s %s", resp.status_code, resp.text[:300])
    except Exception:
        logger.exception("Graph mail failed while marking message as read")


async def _import_messages(db: AsyncSession, messages: list[dict]) -> dict:
    processed = 0
    skipped = 0

    for msg in messages:
        processed_one = await _import_message(db, msg)
        if processed_one:
            processed += 1
        else:
            skipped += 1

    await db.commit()
    for msg in messages:
        if msg.get("processed"):
            await _notify_ticket_recipients(db, msg["ticket_id"], msg["sender_email"])
    return {"processed": processed, "skipped": skipped}


async def _import_message(db: AsyncSession, msg: dict) -> bool:
    if not msg["message_id"]:
        logger.info("Mail reply skipped: missing Message-ID for ticket #%s", msg.get("ticket_id"))
        return False
    exists = await db.execute(select(ProcessedEmail).where(ProcessedEmail.message_id == msg["message_id"]))
    if exists.scalar_one_or_none():
        logger.info("Mail reply skipped: duplicate Message-ID %s", msg["message_id"])
        return False

    ticket = (
        await db.execute(
            select(Ticket)
            .where(Ticket.id == msg["ticket_id"])
            .options(
                selectinload(Ticket.creator),
                selectinload(Ticket.assignee),
                selectinload(Ticket.assignees),
                selectinload(Ticket.watchers),
                selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
            )
        )
    ).scalar_one_or_none()
    if not ticket:
        logger.info("Mail reply skipped: ticket #%s not found", msg["ticket_id"])
        return False

    status_action = msg.get("status_action")
    user = (await db.execute(select(User).where(User.email.ilike(msg["sender_email"])))).scalar_one_or_none()

    # For regular replies (no status change), require a registered sender and body
    if not status_action:
        if not user:
            logger.info("Mail reply skipped: sender %s is not a helpdesk user", msg["sender_email"])
            return False
        if not msg["body"]:
            logger.info("Mail reply skipped: empty body for ticket #%s from %s", msg["ticket_id"], msg["sender_email"])
            return False

    # Add comment from registered user
    if user and msg.get("body"):
        db.add(Comment(body=msg["body"], is_internal=False, ticket_id=ticket.id, author_id=user.id))
        db.add(TicketEvent(ticket_id=ticket.id, actor_id=user.id, event_type="email_reply", message="Resposta recebida por email"))

    # Apply automatic status change
    if status_action:
        try:
            new_status = TicketStatus(status_action)
            old_status = ticket.status.value
            ticket.status = new_status
            status_label = {"closed": "Fechado", "resolved": "Resolvido"}.get(status_action, status_action)
            db.add(TicketEvent(
                ticket_id=ticket.id,
                actor_id=user.id if user else None,
                event_type="status_changed",
                message=f"Estado alterado para {status_label} automaticamente via email ({msg['sender_email']})",
            ))
            logger.info("Mail: ticket #%s status changed %s → %s by email from %s", ticket.id, old_status, status_action, msg["sender_email"])
        except ValueError:
            logger.warning("Mail: unknown status_action %s for ticket #%s", status_action, ticket.id)

    db.add(ProcessedEmail(message_id=msg["message_id"], ticket_id=ticket.id, sender_email=msg["sender_email"]))
    ticket.updated_at = datetime.utcnow()
    msg["processed"] = True
    logger.info("Mail reply imported: ticket #%s from %s (status_action=%s)", ticket.id, msg["sender_email"], status_action)
    return True

def _fetch_unseen_messages(limit: int, force: bool = False) -> list[dict]:
    username = settings.imap_username or settings.mail_username
    password = settings.imap_password or settings.mail_password
    if not username or not password:
        return []

    client_cls = imaplib.IMAP4_SSL if settings.imap_ssl else imaplib.IMAP4
    search_criteria = "ALL" if force else "UNSEEN"
    logger.info(
        "Connecting to IMAP server %s:%s ssl=%s user=%s folder=%s criteria=%s",
        settings.imap_server,
        settings.imap_port,
        settings.imap_ssl,
        username,
        settings.imap_folder,
        search_criteria,
    )
    client = client_cls(settings.imap_server, settings.imap_port)
    try:
        client.login(username, password)
        status, _ = client.select(settings.imap_folder)
        if status != "OK":
            logger.warning("IMAP folder select failed for folder %s with status %s", settings.imap_folder, status)
            return []
        status, data = client.search(None, search_criteria)
        if status != "OK" or not data or not data[0]:
            logger.info("IMAP search found no messages (criteria=%s)", search_criteria)
            return []

        results: list[dict] = []
        all_ids = data[0].split()
        # Take most recent N messages (ids are in ascending order, take last N)
        ids = all_ids[-limit:]
        logger.info("IMAP search found %s message(s) (criteria=%s), checking last %s", len(all_ids), search_criteria, len(ids))
        for msg_id in ids:
            status, fetched = client.fetch(msg_id, "(RFC822)")
            if status != "OK" or not fetched:
                logger.warning("IMAP fetch failed for message id %s with status %s", msg_id, status)
                continue
            raw = fetched[0][1]
            parsed = email.message_from_bytes(raw)
            item = _parse_reply(parsed)
            if item:
                results.append(item)
                if not force:
                    client.store(msg_id, "+FLAGS", "\\Seen")
            else:
                logger.info("IMAP message ignored: no ticket marker found")
        return results
    except Exception:
        logger.exception("IMAP reply sync failed")
        return []
    finally:
        try:
            client.logout()
        except Exception:
            pass


def _parse_reply(msg: Message) -> dict | None:
    subject = _decode_header_value(msg.get("Subject", ""))
    body_raw = _extract_text_body(msg)

    # Try ticket ID from subject first, then from body pattern
    match = TICKET_RE.search(subject) or BODY_TICKET_RE.search(body_raw)
    if not match:
        return None

    status_action = _detect_status_action(subject)
    sender_email = parseaddr(msg.get("From", ""))[1].strip().lower()
    body = _clean_reply_body(body_raw)
    return {
        "message_id": (msg.get("Message-ID") or f"{sender_email}:{subject}:{hash(body)}").strip(),
        "ticket_id": int(match.group(1)),
        "sender_email": sender_email,
        "body": body,
        "status_action": status_action,
    }


def _detect_status_action(subject: str) -> str | None:
    m = CLOSE_SUBJECT_RE.search(subject)
    if not m:
        return None
    return _SUBJECT_STATUS_MAP.get(m.group(1).lower())


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
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_type() == "text/html" and not part.get("Content-Disposition"):
                return _html_to_text(_decode_payload(part))
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


def _html_to_text(body: str) -> str:
    body = re.sub(r"(?is)<(br|/p|/div|/li)\b[^>]*>", "\n", body)
    body = re.sub(r"(?is)<style\b.*?</style>|<script\b.*?</script>", "", body)
    body = re.sub(r"(?s)<[^>]+>", "", body)
    return body.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


async def _notify_ticket_recipients(db: AsyncSession, ticket_id: int, sender_email: str) -> None:
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.creator),
            selectinload(Ticket.assignee),
            selectinload(Ticket.assignees),
            selectinload(Ticket.watchers),
            selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        return

    sender = sender_email.lower()
    recipients: set[str] = set()
    if ticket.creator_email_notifications and ticket.creator.email:
        recipients.add(ticket.creator.email.lower())
    if ticket.assignee and ticket.assignee.email:
        recipients.add(ticket.assignee.email.lower())
    for assignee in getattr(ticket, "assignees", []):
        if assignee.email:
            recipients.add(assignee.email.lower())
    for watcher in ticket.watchers:
        if watcher.email:
            recipients.add(watcher.email.lower())
    if ticket.group:
        for member in ticket.group.members:
            if member.email:
                recipients.add(member.email.lower())
    recipients.discard(sender)

    for recipient in recipients:
        await email_service.send_ticket_notification(
            recipient,
            "updated",
            {"id": ticket.id, "title": ticket.title, "status": ticket.status.value, "message": "Foi recebida uma nova resposta por email."},
        )
