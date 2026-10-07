import asyncio
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Attachment, Comment, TicketEvent, TicketReminder, TicketStatus
from app.models.category import Category
from app.models.school import School
from app.schemas.ticket import visible_attachments, AttachmentRead, TicketCreate, TicketRead, TicketUpdate, PaginatedTickets, TicketListItem, CommentCreate, CommentRead, CommentUpdate, WatcherAdd, TicketRatingCreate, TicketRatingRead
from app.models.planning import TicketRating
from app.services import ticket_service, email_service, push_service, read_service
from app.api.v1.settings import _read_settings
from app.config import settings
from app.services.permissions import has_perm
from app.services import notifications
from app.services.notification_prefs import wants

router = APIRouter(prefix="/tickets", tags=["tickets"])

UPLOAD_DIR = "/app/data/uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Attachments allowed, by extension: stored content type and the file signature the content must start with.
# Anything that a browser could run (HTML, SVG, JS…) is refused.
_OLE = b"\xd0\xcf\x11\xe0"
_ZIP = b"PK\x03\x04"
ALLOWED_ATTACHMENTS: dict[str, tuple[str, tuple[bytes, ...] | None]] = {
    ".png": ("image/png", (b"\x89PNG",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".gif": ("image/gif", (b"GIF87a", b"GIF89a")),
    ".webp": ("image/webp", (b"RIFF",)),
    ".heic": ("image/heic", None),
    ".pdf": ("application/pdf", (b"%PDF",)),
    ".doc": ("application/msword", (_OLE,)),
    ".xls": ("application/vnd.ms-excel", (_OLE,)),
    ".ppt": ("application/vnd.ms-powerpoint", (_OLE,)),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", (_ZIP,)),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", (_ZIP,)),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", (_ZIP,)),
    ".odt": ("application/vnd.oasis.opendocument.text", (_ZIP,)),
    ".ods": ("application/vnd.oasis.opendocument.spreadsheet", (_ZIP,)),
    ".zip": ("application/zip", (_ZIP,)),
    ".txt": ("text/plain", None),
    ".csv": ("text/csv", None),
}
ALLOWED_LABEL = "imagem, PDF, Word, Excel, PowerPoint, OpenDocument, texto ou ZIP"


def _attachment_type(filename: str, content: bytes) -> str | None:
    """Content type to store, or None when the file is not an accepted, genuine document."""
    ext = os.path.splitext(filename or "")[1].lower()
    spec = ALLOWED_ATTACHMENTS.get(ext)
    if not spec:
        return None
    content_type, signatures = spec
    if signatures and not any(content.startswith(sig) for sig in signatures):
        return None
    if ext == ".webp" and content[8:12] != b"WEBP":
        return None
    if content_type.startswith("text/") and (b"\x00" in content[:4096] or b"<script" in content[:4096].lower() or b"<html" in content[:4096].lower()):
        return None
    return content_type


def _can_set_reminder(ticket, user: User) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or user.is_technician:
        return True
    return ticket.assignee_id == user.id or any(a.id == user.id for a in getattr(ticket, "assignees", []))


def _assigned_ids(ticket) -> set[int]:
    return {uid for uid in [ticket.assignee_id, *(a.id for a in getattr(ticket, "assignees", []))] if uid}


MAX_PRIVATE_RECIPIENTS = 20


def _is_staff(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or user.is_technician


async def _private_message_recipients(db: AsyncSession, ticket, sender: User, recipient_ids: list[int]) -> list[User]:
    """Who a private message may go to.
    - Staff, people assigned to the ticket and the Direção (anyone who can see every ticket) can write privately to
      technicians/admins, to the Direção and to anyone in the ticket (requester, assignees, followers).
    - Anyone can answer everyone who is in a private conversation with them on this ticket."""
    ids = list(dict.fromkeys(i for i in recipient_ids if i))
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escolha a quem enviar a mensagem privada.")
    if sender.id in ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não pode enviar uma mensagem privada a si próprio.")
    if len(ids) > MAX_PRIVATE_RECIPIENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No máximo {MAX_PRIVATE_RECIPIENTS} pessoas por mensagem privada.")
    users = {u.id: u for u in (await db.execute(select(User).where(User.id.in_(ids)))).scalars()}
    assigned = _assigned_ids(ticket)
    sender_can_write = _is_staff(sender) or sender.id in assigned or has_perm(sender, "tickets.view_all")
    in_ticket = {ticket.creator_id, *assigned, *(w.id for w in ticket.watchers)}
    # People already in a private conversation with the sender on this ticket
    partners: set[int] = set()
    for c in getattr(ticket, "comments", []):
        if c.deleted_at is None and c.private_to_id:
            people = c.private_participants()
            if sender.id in people:
                partners |= people
    recipients: list[User] = []
    for rid in ids:
        recipient = users.get(rid)
        if not recipient or not recipient.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado.")
        allowed = rid in partners or (sender_can_write and (
            _is_staff(recipient) or rid in in_ticket or has_perm(recipient, "tickets.view_all")
        ))
        if not allowed and not sender_can_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Só pode escrever em privado a quem já lhe escreveu em privado neste ticket ({recipient.display_name} ainda não o fez).",
            )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Não pode enviar uma mensagem privada a {recipient.display_name}: só a técnicos, administradores, "
                       "à Direção ou a pessoas deste ticket (solicitante, responsáveis e seguidores).",
            )
        recipients.append(recipient)
    return recipients


async def _allowed_mentions(db: AsyncSession, ticket, author: User, data, private_recipients: list[User]) -> list[User]:
    """People mentioned with @ who may actually read the message: for a private message its participants, for an
    internal note the support team, otherwise anyone who can open the ticket. Others are silently ignored."""
    ids = [i for i in dict.fromkeys(data.mention_ids or []) if i and i != author.id][:20]
    if not ids:
        return []
    users = (await db.execute(select(User).where(User.id.in_(ids), User.is_active.is_(True)))).scalars().all()
    allowed = []
    for u in users:
        if private_recipients:
            ok = u.id in {p.id for p in private_recipients}
        elif data.is_internal:
            ok = has_perm(u, "tickets.manage") or _is_staff(u)
        else:
            ok = _can_access_ticket(ticket, u) or has_perm(u, "tickets.view_all")
        if ok:
            allowed.append(u)
    return allowed


def _private_comment_visible(comment: Comment, user: User) -> bool:
    return comment.private_to_id is None or user.id in comment.private_participants()


def _can_access_ticket(ticket, user: User, *, allow_watcher: bool = True) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or user.is_technician:
        return True
    if ticket.creator_id == user.id:
        return True
    if any(assignee.id == user.id for assignee in getattr(ticket, "assignees", [])):
        return True
    return allow_watcher and any(watcher.id == user.id for watcher in ticket.watchers)


async def inbox_items(db: AsyncSession, user: User, items) -> list[TicketListItem]:
    """List rows with this viewer's inbox state: unread flag and their own pending reminder (reminders are private)."""
    unread = await read_service.unread_ids(db, user, items)
    reminders = await read_service.pending_reminders(db, user, [t.id for t in items])
    data = [TicketListItem.model_validate(t) for t in items]
    for item in data:
        item.is_unread = item.id in unread
        item.reminder_at = reminders.get(item.id)
        item.has_reminder = item.reminder_at is not None
    return data


@router.get("", response_model=PaginatedTickets)
async def list_tickets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: TicketStatus | None = None,
    category_id: int | None = None,
    search: str | None = Query(None, max_length=200),
    exclude_category_ids: list[int] = Query(default=[]),
    status_in: list[TicketStatus] = Query(default=[]),
    overdue: bool = False,
    expiring: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await ticket_service.list_tickets(db, current_user, page, size, status, category_id, search, exclude_category_ids, status_in, overdue, expiring)
    data = await inbox_items(db, current_user, items)
    return {"items": data, "total": total, "page": page, "size": size}


class ReminderCreate(BaseModel):
    remind_at: datetime
    note: str | None = None


def _utc_naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


async def _my_reminders(db: AsyncSession, ticket_id: int, user: User) -> list[dict]:
    """The viewer's pending reminders on a ticket: set on their own, or attached to one of their replies."""
    own = (await db.execute(select(TicketReminder).where(
        TicketReminder.ticket_id == ticket_id, TicketReminder.user_id == user.id, TicketReminder.sent_at.is_(None),
    ))).scalars().all()
    on_replies = (await db.execute(select(Comment).where(
        Comment.ticket_id == ticket_id, Comment.author_id == user.id, Comment.remind_at.is_not(None),
        Comment.reminder_sent_at.is_(None), Comment.deleted_at.is_(None),
    ))).scalars().all()
    items = [{"id": f"r{r.id}", "remind_at": r.remind_at.isoformat() + "Z", "note": r.note, "source": "lembrete"} for r in own]
    items += [{"id": f"c{c.id}", "remind_at": c.remind_at.isoformat() + "Z", "note": c.body[:140], "source": "resposta"} for c in on_replies]
    return sorted(items, key=lambda i: i["remind_at"])


@router.get("/{ticket_id}/reminders")
async def list_my_reminders(ticket_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _my_reminders(db, ticket_id, current_user)


@router.post("/{ticket_id}/reminders", status_code=status.HTTP_201_CREATED)
async def create_reminder(ticket_id: int, data: ReminderCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.get_ticket_for_access(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    if not _can_set_reminder(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só administradores, técnicos e responsáveis pelo ticket podem criar lembretes.")
    when = _utc_naive(data.remind_at)
    if when <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escolha uma data e hora no futuro para o lembrete.")
    db.add(TicketReminder(ticket_id=ticket_id, user_id=current_user.id, remind_at=when, note=(data.note or "").strip()[:2000] or None))
    await db.commit()
    return await _my_reminders(db, ticket_id, current_user)


@router.put("/{ticket_id}/reminders/mine")
async def set_my_reminder(ticket_id: int, data: ReminderCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """The "Lembrar-me deste ticket" switch: one pending reminder per person and ticket, saved as soon as it changes."""
    ticket = await ticket_service.get_ticket_for_access(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    if not _can_set_reminder(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só administradores, técnicos e responsáveis pelo ticket podem criar lembretes.")
    when = _utc_naive(data.remind_at)
    if when <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escolha uma data e hora no futuro para o lembrete.")
    current = (await db.execute(select(TicketReminder).where(
        TicketReminder.ticket_id == ticket_id, TicketReminder.user_id == current_user.id, TicketReminder.sent_at.is_(None),
    ).order_by(TicketReminder.id))).scalars().all()
    if current:
        current[0].remind_at = when
        for extra in current[1:]:
            await db.delete(extra)
    else:
        db.add(TicketReminder(ticket_id=ticket_id, user_id=current_user.id, remind_at=when))
    await db.commit()
    return await _my_reminders(db, ticket_id, current_user)


@router.delete("/{ticket_id}/reminders/mine")
async def clear_my_reminder(ticket_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(TicketReminder).where(
        TicketReminder.ticket_id == ticket_id, TicketReminder.user_id == current_user.id, TicketReminder.sent_at.is_(None),
    ))).scalars().all()
    for row in rows:
        await db.delete(row)
    await db.commit()
    return await _my_reminders(db, ticket_id, current_user)


@router.delete("/{ticket_id}/reminders/{reminder_id}")
async def cancel_reminder(ticket_id: int, reminder_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    kind, raw = reminder_id[:1], reminder_id[1:]
    if not raw.isdigit():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lembrete não encontrado.")
    if kind == "r":
        row = await db.get(TicketReminder, int(raw))
        if not row or row.user_id != current_user.id or row.ticket_id != ticket_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lembrete não encontrado.")
        await db.delete(row)
    else:
        row = await db.get(Comment, int(raw))
        if not row or row.author_id != current_user.id or row.ticket_id != ticket_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lembrete não encontrado.")
        row.remind_at = None
    await db.commit()
    return await _my_reminders(db, ticket_id, current_user)


class ReadMarks(BaseModel):
    ids: list[int]


@router.post("/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_tickets_read(data: ReadMarks, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await read_service.mark_read(db, current_user.id, list(dict.fromkeys(data.ids))[:500])


@router.post("/{ticket_id}/unread", status_code=status.HTTP_204_NO_CONTENT)
async def mark_ticket_unread(ticket_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ticket = await ticket_service.get_ticket_for_access(db, ticket_id)
    if not ticket or not (_can_access_ticket(ticket, current_user) or has_perm(current_user, "tickets.view_all")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    await read_service.mark_unread(db, current_user.id, ticket_id)


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    category = (await db.execute(select(Category).where(Category.id == data.category_id))).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Categoria obrigatória ou inválida")
    school = (await db.execute(select(School).where(School.id == data.school_id))).scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escola obrigatória ou inválida")

    ticket = await ticket_service.create_ticket(db, data, current_user)
    notified: set[str] = set()
    if ticket.creator_email_notifications:
        await email_service.send_ticket_notification(
            current_user.email,
            "created",
            {"id": ticket.id, "title": ticket.title, "description": ticket.description, "category": ticket.category.name, "priority": ticket.priority.value, "school": ticket.school.name if ticket.school else ""},
        )
        notified.add(current_user.email.lower())
    if ticket.category.email_to:
        await email_service.send_ticket_notification(
            ticket.category.email_to,
            "created",
            {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "category": ticket.category.name,
                "priority": ticket.priority.value,
                "requester": current_user.display_name,
                "school": ticket.school.name if ticket.school else "",
            },
        )
        notified.add(ticket.category.email_to.lower())
    assigned_users = list(ticket.assignees or ([] if not ticket.assignee else [ticket.assignee]))
    await notifications.notify_assigned(ticket, assigned_users, current_user)
    if ticket.group:
        already = {u.id for u in assigned_users}
        await notifications.notify_assigned(ticket, [m for m in ticket.group.members if m.id not in already], current_user, label=ticket.group.name)
    for watcher in ticket.watchers:
        email = watcher.email.lower() if watcher.email else ""
        if email and email not in notified and watcher.id != current_user.id:
            await email_service.send_ticket_notification(
                watcher.email,
                "updated",
                {
                    "id": ticket.id,
                    "title": ticket.title,
                    "status": ticket.status.value,
                    "message": f"{current_user.display_name} deu-lhe conhecimento deste ticket.",
                },
            )
            notified.add(email)

    if data.escalate and (current_user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or current_user.is_technician):
        app_settings = _read_settings()
        provider_email = (app_settings.get("support_provider_email") or "").strip()
        provider_name = (app_settings.get("support_provider_name") or "Fornecedor externo").strip()
        if await notifications.send_to_provider(ticket, "escalated", {"escalated_by": current_user.display_name}):
            ticket.is_escalated = True
            db.add(TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="escalated", message=f"Ticket escalado para {provider_name} ({provider_email}) na criação"))
            await db.commit()

    return ticket


async def _attachment_comment(db: AsyncSession, ticket_id: int, comment_id: int) -> Comment | None:
    return (await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id, Comment.deleted_at.is_(None))
    )).scalar_one_or_none()


@router.post("/{ticket_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    comment_id: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket_for_access(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    comment = None
    if comment_id is not None:
        # A file that goes with one's own reply (private message, internal note…): it gets the reply's visibility
        comment = await _attachment_comment(db, ticket_id, comment_id)
        if not comment or comment.author_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem não encontrada.")
    elif not _can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ficheiro demasiado grande. Máximo: 10 MB.")
    content_type = _attachment_type(file.filename or "", content)
    if not content_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Formato não permitido. Envie {ALLOWED_LABEL}.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored_name), "wb") as f:
        f.write(content)

    attachment = Attachment(
        original_name=file.filename or "anexo",
        stored_name=stored_name,
        content_type=content_type,
        size=len(content),
        ticket_id=ticket_id,
        uploaded_by_id=current_user.id,
        comment_id=comment.id if comment else None,
    )
    db.add(attachment)
    ticket.updated_at = datetime.utcnow()
    # The history is seen by everyone on the ticket: a file of a private message or note stays out of it
    if comment is None or (not comment.private_to_id and not comment.is_internal):
        db.add(TicketEvent(ticket_id=ticket_id, actor_id=current_user.id, event_type="attachment_added", message=f"Anexo adicionado: {attachment.original_name}"))
    await db.commit()
    await db.refresh(attachment)
    return attachment


@router.get("/{ticket_id}/attachments/{attachment_id}/download")
async def download_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket_for_access(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")

    attachment = (
        await db.execute(select(Attachment).where(Attachment.id == attachment_id, Attachment.ticket_id == ticket_id))
    ).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    comment = await _attachment_comment(db, ticket_id, attachment.comment_id) if attachment.comment_id else None
    if attachment.comment_id and not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    if comment is not None and comment.private_to_id:
        # Files of a private message: only the people in that conversation
        people = {comment.author_id, comment.private_to_id, *(u.id for u in comment.private_recipients)}
        if current_user.id not in people:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    else:
        if not _can_access_ticket(ticket, current_user) and not has_perm(current_user, "tickets.view_all"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
        if comment is not None and comment.is_internal and not _is_staff(current_user):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")

    path = os.path.join(UPLOAD_DIR, attachment.stored_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="O ficheiro do anexo já não existe no servidor.")
    # Never let the browser run a stored file as a page: images may show inline, everything else downloads
    inline = attachment.content_type in {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}
    return FileResponse(
        path,
        media_type=attachment.content_type if inline else "application/octet-stream",
        filename=attachment.original_name,
        content_disposition_type="inline" if inline else "attachment",
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
    )


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    if not _can_access_ticket(ticket, current_user) and not has_perm(current_user, "tickets.view_all"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    hide_demo = ticket_service.hides_demo_content(current_user)
    if hide_demo and ticket.creator and ticket.creator.auth_provider == "demo":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    data = TicketRead.model_validate(ticket)
    if current_user.id == ticket.creator_id or has_perm(current_user, "tickets.view_all") or _is_staff(current_user):
        rating = (await db.execute(select(TicketRating).where(TicketRating.ticket_id == ticket.id))).scalar_one_or_none()
        data.rating = TicketRatingRead.model_validate(rating) if rating else None
    await read_service.mark_read(db, current_user.id, [ticket.id])
    if hide_demo:
        data.comments = [c for c in data.comments if c.author is None or c.author.auth_provider != "demo"]
        data.attachments = visible_attachments(data.attachments, data.comments)
    return data


@router.put("/{ticket_id}/rating", response_model=TicketRatingRead)
async def rate_ticket(ticket_id: int, data: TicketRatingCreate, current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """The requester rates the help received, once the ticket is resolved or closed (can change it later)."""
    ticket = await ticket_service.get_ticket_for_access(db, ticket_id)
    if not ticket or ticket.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    if ticket.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Só é possível avaliar depois de o pedido estar resolvido.")
    if not 1 <= data.stars <= 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escolha entre 1 e 5 estrelas.")
    rating = (await db.execute(select(TicketRating).where(TicketRating.ticket_id == ticket_id))).scalar_one_or_none()
    comment = (data.comment or "").strip()[:2000] or None
    if rating:
        rating.stars, rating.comment, rating.updated_at = data.stars, comment, datetime.utcnow()
    else:
        rating = TicketRating(ticket_id=ticket_id, user_id=current_user.id, stars=data.stars, comment=comment)
        db.add(rating)
        db.add(TicketEvent(ticket_id=ticket_id, actor_id=current_user.id, event_type="rated",
                           message=f"Avaliação do requerente: {'★' * data.stars}{'☆' * (5 - data.stars)}"))
    await db.commit()
    await db.refresh(rating)
    return rating


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    if not _can_access_ticket(ticket, current_user, allow_watcher=False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    # Without "Gerir tickets", people may only change their own email preference; status, priority and
    # assignment are the support team's job (the API used to accept them from anyone linked to the ticket)
    if not has_perm(current_user, "tickets.manage"):
        if data.model_fields_set - {"creator_email_notifications"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só a equipa de apoio pode alterar o estado, a prioridade ou a atribuição do ticket.")
        if ticket.creator_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só quem fez o pedido pode alterar as suas notificações por email.")
    content_fields = {"title", "description"}
    if data.model_fields_set & content_fields and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só administradores podem editar o conteúdo do ticket")
    only_email_preference = data.model_fields_set == {"creator_email_notifications"}
    content_changed = bool(data.model_fields_set & content_fields)
    old_status = ticket.status
    previous_assignees = _assigned_ids(ticket)
    updated = await ticket_service.update_ticket(db, ticket, data)
    if not only_email_preference:
        await notify_ticket_changes(updated, current_user, old_status, previous_assignees, content_changed)
    return updated


@router.post("/{ticket_id}/escalate", response_model=TicketRead)
async def escalate_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")

    app_settings = _read_settings()
    provider_email = (app_settings.get("support_provider_email") or "").strip()
    provider_name = (app_settings.get("support_provider_name") or "Fornecedor externo").strip()
    if not provider_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email do fornecedor não configurado")
    if not settings.mail_server:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envio de email não configurado")

    # Everything the support company needs: the request and the public conversation so far
    await notifications.send_to_provider(ticket, "escalated", {"escalated_by": current_user.display_name})
    ticket.is_escalated = True
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="escalated", message=f"Ticket escalado para {provider_name} ({provider_email})"))
    await db.commit()
    return await ticket_service.get_ticket(db, ticket_id)


@router.post("/{ticket_id}/deescalate", response_model=TicketRead)
async def deescalate_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    if not any(e.event_type == "escalated" for e in ticket.events):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket não está escalado")
    app_settings = _read_settings()
    provider_name = (app_settings.get("support_provider_name") or "Fornecedor externo").strip()
    ticket.is_escalated = False
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="deescalated", message=f"Ticket resolvido pelo fornecedor ({provider_name})"))
    await db.commit()
    return await ticket_service.get_ticket(db, ticket_id)


@router.post("/{ticket_id}/comments/{comment_id}/escalate", status_code=status.HTTP_204_NO_CONTENT)
async def escalate_comment(
    ticket_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    if not ticket.is_escalated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket não está reportado à empresa de apoio")
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id, Comment.deleted_at.is_(None)))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comentário não encontrado")
    if comment.is_internal or comment.private_to_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não é possível reenviar notas internas nem mensagens privadas")
    app_settings = _read_settings()
    provider_email = (app_settings.get("support_provider_email") or "").strip()
    provider_name = (app_settings.get("support_provider_name") or "Empresa de apoio").strip()
    if not provider_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email da empresa de apoio não configurado")
    if not settings.mail_server:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envio de email não configurado")
    author = await db.get(User, comment.author_id)
    author_name = author.display_name if author else "Desconhecido"
    # The reply, with the conversation before it (the company may not have seen the earlier messages)
    await notifications.send_to_provider(ticket, "supplier_comment", {"author": author_name, "comment": comment.body},
                                         exclude_comment_id=comment.id)


@router.post("/{ticket_id}/watchers", response_model=TicketRead)
async def add_watcher(
    ticket_id: int,
    data: WatcherAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    is_creator = ticket.creator_id == current_user.id
    is_staff = current_user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or current_user.is_technician
    if not is_creator and not is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    person = await db.get(User, data.user_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado")
    if not any(w.id == person.id for w in ticket.watchers):
        ticket.watchers.append(person)
        ticket.updated_at = datetime.utcnow()
        db.add(TicketEvent(
            ticket_id=ticket_id,
            actor_id=current_user.id,
            event_type="watcher_added",
            message=f"{person.display_name} adicionado(a) em conhecimento",
        ))
        await db.commit()
        await db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}/watchers/{user_id}", response_model=TicketRead)
async def remove_watcher(
    ticket_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    is_creator = ticket.creator_id == current_user.id
    is_staff = current_user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or current_user.is_technician
    if not is_creator and not is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    person = next((w for w in ticket.watchers if w.id == user_id), None)
    if person:
        ticket.watchers.remove(person)
        ticket.updated_at = datetime.utcnow()
        db.add(TicketEvent(
            ticket_id=ticket_id,
            actor_id=current_user.id,
            event_type="watcher_removed",
            message=f"{person.display_name} removido(a) do conhecimento",
        ))
        await db.commit()
        await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def add_comment(
    ticket_id: int,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    private_ids = list(data.private_to_ids or ([data.private_to_id] if data.private_to_id else []))
    # The Direção sees every ticket but only writes in private conversations
    if not _can_access_ticket(ticket, current_user) and not (private_ids and has_perm(current_user, "tickets.view_all")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician:
        data.is_internal = False
    if data.remind_at is not None:
        if not _can_set_reminder(ticket, current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só administradores, técnicos e responsáveis pelo ticket podem criar lembretes.")
        when = data.remind_at if data.remind_at.tzinfo else data.remind_at.replace(tzinfo=timezone.utc)
        if when <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escolha uma data e hora no futuro para o lembrete.")
    new_status = None
    if data.new_status is not None and not private_ids and not data.is_internal:
        if not has_perm(current_user, "tickets.manage"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só a equipa de apoio pode alterar o estado do ticket.")
        new_status = data.new_status if data.new_status != ticket.status else None
    private_recipients: list[User] = []
    if private_ids:
        private_recipients = await _private_message_recipients(db, ticket, current_user, private_ids)
        data.is_internal = False
    mentioned = await _allowed_mentions(db, ticket, current_user, data, private_recipients)
    comment = await ticket_service.add_comment(db, ticket, data, current_user, private_recipients, [u.id for u in mentioned])
    if mentioned:
        await notifications.notify_mentions(ticket, current_user, mentioned, data.body, internal=data.is_internal,
                                            private=bool(private_recipients))

    if private_recipients:
        others = ", ".join(u.display_name for u in private_recipients)
        for person in private_recipients:
            if person.email and wants(person, "private", "email"):
                await email_service.send_private_message(person.email, {
                    "id": ticket.id,
                    "title": ticket.title,
                    "author": current_user.display_name,
                    "comment": data.body,
                    "recipients": others if len(private_recipients) > 1 else "",
                })
        asyncio.create_task(push_service.send_push_to_users_bg(
            {u.id for u in private_recipients if wants(u, "private", "push")},
            f"Mensagem privada: {ticket.title}",
            f"{current_user.display_name}: {data.body[:80]}",
            f"/tickets/{ticket.id}",
        ))
        return comment

    # Auto-subscribe the commenter as watcher so they receive future updates
    is_linked = (
        current_user.id == ticket.creator_id
        or current_user.id == ticket.assignee_id
        or any(a.id == current_user.id for a in getattr(ticket, "assignees", []))
        or any(w.id == current_user.id for w in ticket.watchers)
    )
    if not is_linked:
        ticket.watchers.append(current_user)
        db.add(TicketEvent(
            ticket_id=ticket_id,
            actor_id=current_user.id,
            event_type="watcher_added",
            message=f"{current_user.display_name} passou a seguir o ticket ao responder",
        ))
        await db.commit()

    if new_status is not None:
        ticket.status = new_status
        db.add(TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="updated",
                           message=f"Estado alterado para {ticket_service._STATUS_PT.get(new_status.value, new_status.value)}"))
        await db.commit()
        ticket = await ticket_service.get_ticket(db, ticket_id)

    if current_user.id == ticket.creator_id and not data.is_internal:
        from app.services import teams_service
        teams_service.requester_reply(ticket, data.body)
    if not data.is_internal:
        # One email per person with the reply and, if it changed, the new state
        await notifications.notify_reply(ticket, current_user, data.body, new_status, comment_id=comment.id)
        if new_status is not None and ticket.is_escalated and new_status in notifications.DONE_STATES:
            await notifications.send_to_provider(ticket, "supplier_updated", {"editor": current_user.display_name})
    return comment


@router.patch("/{ticket_id}/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    ticket_id: int,
    comment_id: int,
    data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id, Comment.deleted_at.is_(None)))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada.")
    if not _private_comment_visible(comment, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada.")
    if comment.private_to_id and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só o autor pode alterar uma mensagem privada.")
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    comment.ticket = ticket
    updated = await ticket_service.update_comment(db, comment, data.body)
    return updated


@router.delete("/{ticket_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    ticket_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket não encontrado.")
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id, Comment.deleted_at.is_(None)))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada.")
    if not _private_comment_visible(comment, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada.")
    if comment.private_to_id and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só o autor pode alterar uma mensagem privada.")
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem acesso a este ticket.")
    comment.ticket = ticket
    await ticket_service.delete_comment(db, comment)


async def notify_ticket_changes(ticket, actor: User, old_status, previous_assignees: set[int], content_changed: bool = False) -> None:
    """After a ticket was edited (state, priority, group, assignees, content): who is told, see services/notifications."""
    if ticket.status != old_status:
        await notifications.notify_status(ticket, actor, old_status, ticket.status)
    new_people = [u for u in [*getattr(ticket, "assignees", []), *([ticket.assignee] if ticket.assignee else [])]
                  if u.id not in previous_assignees]
    if new_people:
        await notifications.notify_assigned(ticket, list({u.id: u for u in new_people}.values()), actor)
    if content_changed:
        payload = {"id": ticket.id, "title": ticket.title, "status": ticket.status.value, "editor": actor.display_name}
        for recipient in _ticket_update_recipients(ticket, actor):
            await email_service.send_ticket_notification(recipient, "content_updated", payload)


def _ticket_update_recipients(ticket, current_user: User) -> set[str]:
    recipients: set[str] = set()

    def add_recipient(user_id: int, email: str | None):
        if not email or user_id == current_user.id:
            return
        if user_id == ticket.creator_id and not ticket.creator_email_notifications:
            return
        recipients.add(email)

    if ticket.creator.email and ticket.creator_email_notifications and current_user.id != ticket.creator_id:
        recipients.add(ticket.creator.email)

    if ticket.assignee:
        add_recipient(ticket.assignee_id, ticket.assignee.email)
    for assignee in getattr(ticket, "assignees", []):
        add_recipient(assignee.id, assignee.email)
    if ticket.group:
        for member in ticket.group.members:
            add_recipient(member.id, member.email)
    for watcher in ticket.watchers:
        add_recipient(watcher.id, watcher.email)
    
    if ticket.category.email_to:
        recipients.add(ticket.category.email_to)

    # Foolproof final filters
    if current_user.email:
        recipients.discard(current_user.email)
    if not ticket.creator_email_notifications and ticket.creator.email:
        recipients.discard(ticket.creator.email)

    return recipients
