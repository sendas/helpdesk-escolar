"""Caixa de entrada: the helpdesk mailbox inside the app. People with "mailbox.read" read it; the support team can
turn an email into a ticket or add it to an existing one (with its attachments)."""
import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_perm
from app.models.ticket import Attachment, Comment, ProcessedEmail, TicketEvent, TicketPriority
from app.models.user import User
from app.services import mailbox as mb
from app.services.permissions import has_perm

router = APIRouter(prefix="/mailbox", tags=["mailbox"])
logger = logging.getLogger(__name__)


def _provider():
    provider = mb.get_provider()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="A caixa de correio do helpdesk não está ligada (configure o Microsoft 365 ou IMAP no app.env).")
    return provider


async def _run(coro):
    try:
        return await coro
    except mb.MailboxError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        # Say what went wrong instead of a bare "Internal Server Error"
        logger.exception("Caixa de entrada: erro inesperado")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Erro inesperado na caixa de correio ({exc.__class__.__name__}: {str(exc)[:160]}).") from exc


async def _linked(db: AsyncSession, message_ids: list[str]) -> dict[str, int]:
    ids = [m for m in message_ids if m]
    if not ids:
        return {}
    rows = (await db.execute(select(ProcessedEmail.message_id, ProcessedEmail.ticket_id).where(ProcessedEmail.message_id.in_(ids)))).all()
    return {m: t for m, t in rows}


def _ticket_hint(subject: str) -> int | None:
    from app.services.email_ingest import TICKET_RE
    m = TICKET_RE.search(subject or "")
    return int(m.group(1)) if m else None


@router.get("")
async def list_mail(page: int = Query(1, ge=1, le=200), db: AsyncSession = Depends(get_db),
                    _: User = Depends(require_perm("mailbox.read"))):
    provider = mb.get_provider()
    if provider is None:
        return {"configured": False, "items": [], "has_more": False, "mailbox": mb.mailbox_address()}
    items, has_more = await _run(provider.list(page))
    linked = await _linked(db, [i.internet_message_id for i in items])
    senders = {i.from_email for i in items if i.from_email}
    known = set()
    if senders:
        known = {e for (e,) in (await db.execute(select(func.lower(User.email)).where(func.lower(User.email).in_(senders)))).all()}
    return {
        "configured": True, "provider": provider.name, "mailbox": mb.mailbox_address(), "page": page, "has_more": has_more,
        "can_archive": getattr(provider, "can_archive", True), "can_delete": getattr(provider, "can_archive", True),
        "items": [{**i.__dict__, "ticket_id": linked.get(i.internet_message_id), "ticket_hint": _ticket_hint(i.subject),
                   "sender_known": i.from_email in known} for i in items],
    }


@router.get("/message")
async def get_mail(id: str = Query(..., max_length=500), db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("mailbox.read"))):
    m = await _run(_provider().get(id))
    linked = await _linked(db, [m.internet_message_id])
    sender = (await db.execute(select(User).where(func.lower(User.email) == m.from_email).order_by(User.is_active.desc()))).scalars().first() if m.from_email else None
    return {
        **{k: v for k, v in m.__dict__.items() if k != "attachments"},
        "attachments": [{"name": a.name, "content_type": a.content_type, "size": a.size} for a in m.attachments],
        "ticket_id": linked.get(m.internet_message_id), "ticket_hint": _ticket_hint(m.subject),
        "sender": {"id": sender.id, "display_name": sender.display_name} if sender else None,
    }


class MessageRef(BaseModel):
    id: str


class ReadIn(MessageRef):
    read: bool = True


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_mail(data: ReadIn, _: User = Depends(require_perm("mailbox.read"))):
    await _run(_provider().set_read(data.id, data.read))


@router.post("/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_mail(data: MessageRef, _: User = Depends(require_perm("mailbox.read"))):
    await _run(_provider().archive(data.id))


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mail(data: MessageRef, user: User = Depends(require_perm("mailbox.read"))):
    _require_team(user, "eliminar emails")
    await _run(_provider().delete(data.id))


def _require_team(user: User, what: str) -> None:
    if not has_perm(user, "tickets.manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Só a equipa de apoio pode {what}.")


def _signed(text: str, user: User) -> str:
    """Replies go out from the helpdesk address: say who wrote them."""
    from app.api.v1.settings import _read_settings
    org = _read_settings().get("org_name") or "Helpdesk"
    import re
    # "Tiago Costa Docente-550 - Informática" → "Tiago Costa"
    name = re.split(r"\s+Docente[-\s]*\d", user.display_name or "", maxsplit=1)[0].split(" - ")[0].strip() or user.display_name
    return f"{text.strip()}\n\n--\n{name}\nCentro de Apoio Digital · {org}"


class ReplyIn(MessageRef):
    text: str
    reply_all: bool = False


@router.post("/reply", status_code=status.HTTP_204_NO_CONTENT)
async def reply_mail(data: ReplyIn, user: User = Depends(require_perm("mailbox.read"))):
    """Answer an email from the helpdesk mailbox (the original is quoted below, as in Outlook)."""
    _require_team(user, "responder a emails")
    if not data.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escreva a resposta.")
    await _run(_provider().reply(data.id, _signed(data.text, user)[:20000], data.reply_all))
    logger.info("Caixa de entrada: %s respondeu%s ao email %s", user.email, " a todos" if data.reply_all else "", data.id[:40])
    try:
        await _provider().set_read(data.id, True)
    except (mb.MailboxError, HTTPException):
        pass


class ForwardIn(MessageRef):
    to: list[str]
    text: str = ""


@router.post("/forward", status_code=status.HTTP_204_NO_CONTENT)
async def forward_mail(data: ForwardIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_perm("mailbox.read"))):
    """Forward an email (with its attachments) to people of the Agrupamento or any address."""
    import re
    _require_team(user, "reencaminhar emails")
    emails = list(dict.fromkeys(e.strip().lower() for e in data.to if e.strip()))[:30]
    if not emails:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escolha pelo menos um destinatário.")
    bad = [e for e in emails if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e)]
    if bad:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Endereço inválido: {bad[0]}")
    names = dict((e, n) for e, n in (await db.execute(select(func.lower(User.email), User.display_name).where(func.lower(User.email).in_(emails)))).all())
    await _run(_provider().forward(data.id, [(e, names.get(e, "")) for e in emails], _signed(data.text, user) if data.text.strip() else _signed("", user).strip()))
    logger.info("Caixa de entrada: %s reencaminhou o email %s para %s", user.email, data.id[:40], ", ".join(emails))


async def _copy_attachments(db: AsyncSession, message: mb.MailMessage, ticket_id: int, user_id: int) -> tuple[int, list[str]]:
    """Save the email's attachments on the ticket; files of a type the app does not accept are skipped."""
    from app.api.v1.tickets import MAX_UPLOAD_BYTES, UPLOAD_DIR, _attachment_type
    saved, skipped = 0, []
    for a in message.attachments:
        content = a.content or b""
        content_type = _attachment_type(a.name, content) if content and len(content) <= MAX_UPLOAD_BYTES else None
        if not content_type:
            skipped.append(a.name)
            continue
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        stored = f"{uuid.uuid4().hex}{os.path.splitext(a.name)[1].lower()}"
        with open(os.path.join(UPLOAD_DIR, stored), "wb") as f:
            f.write(content)
        db.add(Attachment(original_name=a.name[:255], stored_name=stored, content_type=content_type, size=len(content),
                          ticket_id=ticket_id, uploaded_by_id=user_id))
        saved += 1
    return saved, skipped


def _email_text(message: mb.MailMessage) -> str:
    who = f"{message.from_name} <{message.from_email}>" if message.from_name else message.from_email
    return f"Email de {who}:\n\n{message.body or message.preview}".strip()


class NewTicketIn(MessageRef):
    category_id: int
    school_id: int
    priority: TicketPriority = TicketPriority.MEDIUM
    title: str | None = None


@router.post("/ticket")
async def ticket_from_mail(data: NewTicketIn, db: AsyncSession = Depends(get_db),
                           user: User = Depends(require_perm("mailbox.read"))):
    """New ticket from an email. The sender is the requester when they have an account; otherwise the ticket is
    opened by whoever does this, with the sender's details in the description."""
    if not has_perm(user, "tickets.manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só a equipa de apoio pode criar tickets a partir de emails.")
    from app.schemas.ticket import TicketCreate
    from app.services import notifications, ticket_service
    message = await _run(_provider().get(data.id, with_content=True))
    if message.internet_message_id and (await _linked(db, [message.internet_message_id])):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este email já está ligado a um ticket.")
    requester = None
    if message.from_email:
        requester = (await db.execute(select(User).where(func.lower(User.email) == message.from_email, User.is_active.is_(True)))).scalars().first()
    body = message.body or message.preview or "(email sem texto)"
    description = body if requester else _email_text(message)
    ticket = await ticket_service.create_ticket(db, TicketCreate(
        title=(data.title or message.subject or "Pedido por email").strip()[:200], description=description,
        category_id=data.category_id, school_id=data.school_id, priority=data.priority,
    ), requester or user)
    saved, skipped = await _copy_attachments(db, message, ticket.id, (requester or user).id)
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=user.id, event_type="from_email",
                       message=f"Criado a partir de um email de {message.from_email} por {user.display_name}"))
    if message.internet_message_id:
        db.add(ProcessedEmail(message_id=message.internet_message_id, ticket_id=ticket.id, sender_email=message.from_email))
    await db.commit()
    try:
        await _provider().set_read(data.id, True)
    except (mb.MailboxError, HTTPException):
        pass
    ticket = await ticket_service.get_ticket(db, ticket.id)
    assigned = list(ticket.assignees or ([ticket.assignee] if ticket.assignee else []))
    if assigned:
        await notifications.notify_assigned(ticket, assigned, user)
    return {"ticket_id": ticket.id, "attachments": saved, "skipped": skipped, "requester_found": requester is not None}


class AttachIn(MessageRef):
    ticket_id: int
    internal: bool = False


@router.post("/attach")
async def attach_mail(data: AttachIn, db: AsyncSession = Depends(get_db),
                      user: User = Depends(require_perm("mailbox.read"))):
    """Add an email to an existing ticket, as a reply (or an internal note), with its attachments."""
    if not has_perm(user, "tickets.manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só a equipa de apoio pode juntar emails a tickets.")
    from app.services import notifications, ticket_service
    ticket = await ticket_service.get_ticket(db, data.ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    message = await _run(_provider().get(data.id, with_content=True))
    if message.internet_message_id and (await _linked(db, [message.internet_message_id])):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este email já está ligado a um ticket.")
    sender = None
    if message.from_email:
        sender = (await db.execute(select(User).where(func.lower(User.email) == message.from_email, User.is_active.is_(True)))).scalars().first()
    linked_sender = sender is not None and (sender.id == ticket.creator_id or any(a.id == sender.id for a in ticket.assignees)
                                             or any(w.id == sender.id for w in ticket.watchers))
    author = sender if linked_sender and not data.internal else user
    text = (message.body or message.preview) if author is sender else _email_text(message)
    db.add(Comment(body=text, is_internal=data.internal, ticket_id=ticket.id, author_id=author.id))
    saved, skipped = await _copy_attachments(db, message, ticket.id, author.id)
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=user.id, event_type="email_attached",
                       message=f"Email de {message.from_email} junto ao ticket por {user.display_name}"))
    if message.internet_message_id:
        db.add(ProcessedEmail(message_id=message.internet_message_id, ticket_id=ticket.id, sender_email=message.from_email))
    ticket.updated_at = datetime.utcnow()
    await db.commit()
    try:
        await _provider().set_read(data.id, True)
    except (mb.MailboxError, HTTPException):
        pass
    if not data.internal:
        ticket = await ticket_service.get_ticket(db, ticket.id)
        await notifications.notify_reply(ticket, author, text)
    return {"ticket_id": ticket.id, "attachments": saved, "skipped": skipped}
