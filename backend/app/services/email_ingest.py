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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.group import HelpdeskGroup
from app.models.ticket import Comment, ProcessedEmail, Ticket, TicketEvent, TicketStatus
from app.models.user import User
from app.services import email_service
from app.services.permissions import permissions_for

TICKET_RE = re.compile(r"\[Ticket\s+#(\d+)\]", re.IGNORECASE)
# Matches "O Seu Ticket de Apoio ao Cliente [Ticket #XX]" in the body
BODY_TICKET_RE = re.compile(r"O\s+Seu\s+Ticket\s+de\s+Apoio\s+ao\s+Cliente\s*[\r\n\s]*\[Ticket\s*#(\d+)\]", re.IGNORECASE)
# Subject keywords that trigger automatic ticket status change
# Replies to a private message keep the "[Privada]" marker in the subject
PRIVATE_SUBJECT_RE = re.compile(r"\[Privada\]", re.IGNORECASE)
# The support company's own ticket number in the subject, e.g. "… (#8591)" or "[#8591]" (never our "[Ticket #12]")
PROVIDER_REF_RE = re.compile(r"[(\[]#(\d{2,10})[)\]]")
# …or their acknowledgement: "Pedido de suporte registado com o nº 10288"
PROVIDER_ACK_RE = re.compile(r"\bregistad[oa]\b.*?\bn\.?\s*[ºo°]\s*(\d{2,10})\b", re.IGNORECASE)
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
    # Only now, with the replies saved, are the messages marked as read: if the import failed they are tried again
    # on the next round (Message-IDs already imported are skipped)
    handled = [m for m in messages if not m.get("failed")]
    if provider == "graph":
        await _mark_graph_messages_read([m["graph_id"] for m in handled if m.get("graph_id")])
    elif not force:
        await asyncio.to_thread(_mark_imap_seen, [m["imap_id"] for m in handled if m.get("imap_id")])
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
                item["graph_id"] = raw["id"]
                results.append(item)
            else:
                logger.info("Graph mail message ignored: subject does not contain ticket marker")
        return results


async def _mark_graph_messages_read(ids: list[str]) -> None:
    if not ids:
        return
    mailbox = (settings.graph_mail_user or settings.imap_username or settings.mail_username or settings.mail_from).strip()
    token = await asyncio.to_thread(_get_graph_token)
    if not token or not mailbox:
        return
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        for message_id in ids:
            await _mark_graph_message_read(client, mailbox, message_id, headers)


def _get_graph_token() -> str | None:
    app = msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        timeout=20,
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
        "status_action": None if PRIVATE_SUBJECT_RE.search(subject) else status_action,
        "private": bool(PRIVATE_SUBJECT_RE.search(subject)),
        "provider_ref": _provider_ref(subject),
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
        try:
            processed_one = await _import_message(db, msg)
            await db.commit()
        except Exception:
            await db.rollback()
            msg["failed"] = True
            msg["processed"] = False
            logger.exception("Mail reply import failed for ticket #%s (%s)", msg.get("ticket_id"), msg.get("message_id"))
            skipped += 1
            continue
        if processed_one:
            processed += 1
        else:
            skipped += 1

    for msg in messages:
        if msg.get("processed"):
            from app.services.realtime_hooks import notify_ticket
            await notify_ticket(msg["ticket_id"])
            if msg.get("body") and not msg.get("private") and not msg.get("status_action"):
                from app.services import teams_service, ticket_service
                ticket = await ticket_service.get_ticket(db, msg["ticket_id"])
                if ticket and ticket.creator and (ticket.creator.email or "").lower() == msg["sender_email"].lower():
                    teams_service.requester_reply(ticket, msg["body"])
        if msg.get("processed") and msg.get("private_to_id"):
            await _notify_private_partner(db, msg)
        elif msg.get("processed") and not msg.get("private"):
            await _notify_ticket_recipients(db, msg)
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
    sender = (msg.get("sender_email") or "").strip().lower()
    user = (await db.execute(select(User).where(func.lower(User.email) == sender, User.is_active.is_(True)))).scalar_one_or_none() if sender else None

    # Only people who are part of the ticket (or the support team) may reply by email; the From address is
    # otherwise trivial to fake, so strangers must never be able to post or change a ticket
    linked = bool(user) and (
        user.id == ticket.creator_id
        or user.id == ticket.assignee_id
        or any(a.id == user.id for a in ticket.assignees)
        or any(w.id == user.id for w in ticket.watchers)
        or bool(ticket.group and any(m.id == user.id for m in ticket.group.members))
        or "tickets.manage" in permissions_for(user)
        # The Direção sees every ticket and may answer private conversations
        or (bool(msg.get("private")) and "tickets.view_all" in permissions_for(user))
    )
    from app.api.v1.settings import _read_settings
    provider = (_read_settings().get("support_provider_email") or "").strip().lower()
    is_provider = is_provider_address(sender, provider)
    ref = msg.get("provider_ref")
    if is_provider and ref and ticket.provider_ref != ref and str(ticket.id) != ref:
        # Their number for this ticket: later emails to them carry it, so they land in the same ticket
        ticket.provider_ref = ref
        db.add(TicketEvent(ticket_id=ticket.id, actor_id=None, event_type="provider_ref",
                           message=f"Número do pedido na empresa de apoio: #{ref}"))
    if not linked and not (is_provider and status_action):
        logger.info("Mail reply skipped: %s is not part of ticket #%s", sender, ticket.id)
        return False

    # Closing/resolving by email: only the requester, the support team or the configured support company
    if status_action:
        may_close = is_provider or (user is not None and (user.id == ticket.creator_id or "tickets.manage" in permissions_for(user)))
        if not may_close:
            logger.info("Mail status change ignored: %s may not close ticket #%s", sender, ticket.id)
            status_action = None
            msg["status_action"] = None

    if not status_action and not msg.get("body"):
        logger.info("Mail reply skipped: empty body for ticket #%s from %s", msg["ticket_id"], sender)
        return False

    # Add comment from registered user
    partner_ids = await _private_partners(db, ticket.id, user.id) if user and msg.get("private") else []
    if user and msg.get("body") and partner_ids:
        partners = list((await db.execute(select(User).where(User.id.in_(partner_ids)))).scalars())
        db.add(Comment(body=msg["body"], is_internal=False, ticket_id=ticket.id, author_id=user.id,
                       private_to_id=partner_ids[0], private_recipients=partners))
        msg["private_to_id"] = partner_ids[0]
        msg["private_to_ids"] = partner_ids
    elif user and msg.get("private"):
        # Never turn a reply to a private message into a public one
        logger.info("Mail reply to private message ignored: no private conversation for %s on ticket #%s", msg["sender_email"], ticket.id)
    elif user and msg.get("body"):
        db.add(Comment(body=msg["body"], is_internal=False, ticket_id=ticket.id, author_id=user.id))
        db.add(TicketEvent(ticket_id=ticket.id, actor_id=user.id, event_type="email_reply", message="Resposta recebida por email"))

    # Apply automatic status change
    if status_action:
        try:
            new_status = TicketStatus(status_action)
            msg["old_status"] = ticket.status.value
            old_status = ticket.status.value
            ticket.status = new_status
            ticket.closed_via_email = True
            status_label = {"closed": "Fechado", "resolved": "Resolvido"}.get(status_action, status_action)
            if is_provider and ticket.is_escalated and new_status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
                # The company closed it on their side: nothing more to send them
                ticket.is_escalated = False
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
            # PEEK: fetching must not mark the message as read yet (see sync_inbound_replies)
            status, fetched = client.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK" or not fetched:
                logger.warning("IMAP fetch failed for message id %s with status %s", msg_id, status)
                continue
            raw = fetched[0][1]
            parsed = email.message_from_bytes(raw)
            item = _parse_reply(parsed)
            if item:
                item["imap_id"] = msg_id
                results.append(item)
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


def _mark_imap_seen(ids: list[bytes]) -> None:
    if not ids:
        return
    username = settings.imap_username or settings.mail_username
    password = settings.imap_password or settings.mail_password
    client_cls = imaplib.IMAP4_SSL if settings.imap_ssl else imaplib.IMAP4
    client = client_cls(settings.imap_server, settings.imap_port)
    try:
        client.login(username, password)
        if client.select(settings.imap_folder)[0] != "OK":
            return
        for msg_id in ids:
            client.store(msg_id, "+FLAGS", "\\Seen")
    except Exception:
        logger.exception("IMAP: não foi possível marcar as mensagens como lidas")
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
        "status_action": None if PRIVATE_SUBJECT_RE.search(subject) else status_action,
        "private": bool(PRIVATE_SUBJECT_RE.search(subject)),
        "provider_ref": _provider_ref(subject),
    }


NEGATED_STATUS_RE = re.compile(r"\bn[ãa]o\s+(?:est[áa]\s+|foi\s+|ficou\s+)?(?:fechado|resolvido|resolved|closed)\b", re.IGNORECASE)


def _provider_ref(subject: str) -> str | None:
    m = PROVIDER_REF_RE.search(subject or "") or PROVIDER_ACK_RE.search(subject or "")
    return m.group(1) if m else None


def is_provider_address(sender: str, provider: str) -> bool:
    """The configured address, or any address of the same company — their helpdesk sends from another one,
    e.g. notifications=empresa.pt@mg.empresa.pt for suporte@empresa.pt."""
    sender, provider = (sender or "").strip().lower(), (provider or "").strip().lower()
    if not sender or not provider:
        return False
    if sender == provider:
        return True
    domain = provider.rsplit("@", 1)[-1]
    sender_domain = sender.rsplit("@", 1)[-1]
    return bool(domain) and (sender_domain == domain or sender_domain.endswith("." + domain))


def _detect_status_action(subject: str) -> str | None:
    # "não resolvido" / "not closed" style subjects must never close a ticket
    if NEGATED_STATUS_RE.search(subject) or re.search(r"\bnot\s+(?:resolved|closed)\b", subject, re.IGNORECASE):
        return None
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


async def _private_partners(db: AsyncSession, ticket_id: int, user_id: int) -> list[int]:
    """Who an emailed reply to a private message goes to: everyone else in the last private conversation this user
    took part in on the ticket."""
    from app.models.ticket import comment_private_recipients as cpr
    last = (
        await db.execute(
            select(Comment)
            .where(
                Comment.ticket_id == ticket_id,
                Comment.private_to_id.is_not(None),
                Comment.deleted_at.is_(None),
                (Comment.private_to_id == user_id) | (Comment.author_id == user_id)
                | Comment.id.in_(select(cpr.c.comment_id).where(cpr.c.user_id == user_id)),
            )
            .order_by(Comment.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not last:
        return []
    return sorted(last.private_participants() - {user_id})


async def _notify_private_partner(db: AsyncSession, msg: dict) -> None:
    ticket = await db.get(Ticket, msg["ticket_id"])
    sender = (await db.execute(select(User).where(func.lower(User.email) == msg["sender_email"].lower()))).scalar_one_or_none()
    people = (await db.execute(select(User).where(User.id.in_(msg.get("private_to_ids") or [msg["private_to_id"]])))).scalars().all()
    if not ticket:
        return
    names = ", ".join(p.display_name for p in people)
    for partner in people:
        if not partner.email:
            continue
        await email_service.send_private_message(partner.email, {
            "id": ticket.id,
            "title": ticket.title,
            "author": sender.display_name if sender else msg["sender_email"],
            "comment": msg.get("body") or "",
            "recipients": names if len(people) > 1 else "",
        })


async def _notify_ticket_recipients(db: AsyncSession, msg: dict) -> None:
    """A reply (and/or a state change) that arrived by email: the same notifications as in the app."""
    from app.services import notifications, ticket_service
    ticket = await ticket_service.get_ticket(db, msg["ticket_id"])
    if not ticket:
        return
    sender = (await db.execute(select(User).where(func.lower(User.email) == msg["sender_email"].lower()))).scalar_one_or_none()
    new_status = TicketStatus(msg["status_action"]) if msg.get("status_action") else None
    if msg.get("body") and sender is not None:
        await notifications.notify_reply(ticket, sender, msg["body"], new_status)
    elif new_status is not None and msg.get("old_status"):
        # e.g. the support company closing the ticket from its own mailbox
        await notifications.notify_status(ticket, sender, TicketStatus(msg["old_status"]), new_status)
