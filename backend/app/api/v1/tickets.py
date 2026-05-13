import asyncio
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Attachment, Comment, TicketEvent, TicketStatus
from app.models.category import Category
from app.models.school import School
from app.schemas.ticket import AttachmentRead, TicketCreate, TicketRead, TicketUpdate, PaginatedTickets, CommentCreate, CommentRead, CommentUpdate, WatcherAdd
from app.services import ticket_service, email_service, push_service
from app.api.v1.settings import _read_settings
from app.config import settings

router = APIRouter(prefix="/tickets", tags=["tickets"])

UPLOAD_DIR = "/app/data/uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MIME_PREFIXES = ("image/",)
ALLOWED_CONTENT_TYPES_EXACT = {"application/pdf", "application/octet-stream"}


def _can_access_ticket(ticket, user: User, *, allow_watcher: bool = True) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or user.is_technician:
        return True
    if ticket.creator_id == user.id:
        return True
    if any(assignee.id == user.id for assignee in getattr(ticket, "assignees", [])):
        return True
    return allow_watcher and any(watcher.id == user.id for watcher in ticket.watchers)


@router.get("", response_model=PaginatedTickets)
async def list_tickets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: TicketStatus | None = None,
    category_id: int | None = None,
    search: str | None = Query(None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await ticket_service.list_tickets(db, current_user, page, size, status, category_id, search)
    return {"items": items, "total": total, "page": page, "size": size}


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
    for assignee in assigned_users:
        if not assignee.email:
            continue
        await email_service.send_ticket_notification(
            assignee.email,
            "assigned",
            {"id": ticket.id, "title": ticket.title, "assignee": assignee.display_name},
        )
        notified.add(assignee.email.lower())
    if ticket.group:
        for member in ticket.group.members:
            email = member.email.lower() if member.email else ""
            if email and email not in notified:
                await email_service.send_ticket_notification(
                    member.email,
                    "assigned",
                    {"id": ticket.id, "title": ticket.title, "assignee": ticket.group.name},
                )
                notified.add(email)
    for watcher in ticket.watchers:
        email = watcher.email.lower() if watcher.email else ""
        if email and email not in notified:
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
        if provider_email and settings.mail_server:
            await email_service.send_ticket_notification(
                provider_email,
                "escalated",
                {
                    "id": ticket.id,
                    "title": ticket.title,
                    "description": ticket.description,
                    "requester": ticket.creator.display_name,
                    "requester_email": ticket.creator.email,
                    "category": ticket.category.name,
                    "priority": ticket.priority.value,
                    "school": ticket.school.name if ticket.school else "",
                    "provider": provider_name,
                    "escalated_by": current_user.display_name,
                },
            )
            db.add(TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="escalated", message=f"Ticket escalado para {provider_name} ({provider_email}) na criação"))
            await db.commit()

    # Push notifications for ticket creation
    push_user_ids: set[int] = set()
    if ticket.assignee_id:
        push_user_ids.add(ticket.assignee_id)
    for assignee in ticket.assignees:
        push_user_ids.add(assignee.id)
    if ticket.group:
        for m in ticket.group.members:
            push_user_ids.add(m.id)
    for w in ticket.watchers:
        push_user_ids.add(w.id)
    push_user_ids.discard(current_user.id)
    if push_user_ids:
        asyncio.create_task(push_service.send_push_to_users_bg(
            push_user_ids,
            f"Novo ticket: {ticket.title}",
            f"Pedido de {current_user.display_name}",
            f"/tickets/{ticket.id}",
        ))

    return ticket


@router.post("/{ticket_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ct = (file.content_type or "").lower()
    if not (any(ct.startswith(p) for p in ALLOWED_MIME_PREFIXES) or ct in ALLOWED_CONTENT_TYPES_EXACT):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido. Use imagem ou PDF.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ficheiro demasiado grande. Máximo: 10 MB.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored_name), "wb") as f:
        f.write(content)

    attachment = Attachment(
        original_name=file.filename or "anexo",
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        ticket_id=ticket_id,
        uploaded_by_id=current_user.id,
    )
    db.add(attachment)
    ticket.updated_at = datetime.utcnow()
    db.add(TicketEvent(ticket_id=ticket_id, actor_id=current_user.id, event_type="attachment_added", message=f"Anexo adicionado: {attachment.original_name}"))
    await db.commit()
    await db.refresh(attachment)
    for recipient in _ticket_update_recipients(ticket, current_user):
        await email_service.send_ticket_notification(
            recipient,
            "updated",
            {"id": ticket.id, "title": ticket.title, "status": ticket.status.value},
        )
    return attachment


@router.get("/{ticket_id}/attachments/{attachment_id}/download")
async def download_attachment(
    ticket_id: int,
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    attachment = (
        await db.execute(select(Attachment).where(Attachment.id == attachment_id, Attachment.ticket_id == ticket_id))
    ).scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    path = os.path.join(UPLOAD_DIR, attachment.stored_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_access_ticket(ticket, current_user, allow_watcher=False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    content_fields = {"title", "description"}
    if data.model_fields_set & content_fields and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só administradores podem editar o conteúdo do ticket")
    only_email_preference = data.model_fields_set == {"creator_email_notifications"}
    content_changed = bool(data.model_fields_set & content_fields)
    updated = await ticket_service.update_ticket(db, ticket, data)
    if not only_email_preference:
        notif_type = "content_updated" if content_changed else "updated"
        payload: dict = {"id": updated.id, "title": updated.title, "status": updated.status.value}
        if content_changed:
            payload["editor"] = current_user.display_name
        for recipient in _ticket_update_recipients(updated, current_user):
            await email_service.send_ticket_notification(recipient, notif_type, payload)
    return updated


@router.post("/{ticket_id}/escalate", response_model=TicketRead)
async def escalate_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    app_settings = _read_settings()
    provider_email = (app_settings.get("support_provider_email") or "").strip()
    provider_name = (app_settings.get("support_provider_name") or "Fornecedor externo").strip()
    if not provider_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email do fornecedor não configurado")
    if not settings.mail_server:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envio de email não configurado")

    await email_service.send_ticket_notification(
        provider_email,
        "escalated",
        {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "requester": ticket.creator.display_name,
            "requester_email": ticket.creator.email,
            "category": ticket.category.name,
            "priority": ticket.priority.value,
            "school": ticket.school.name if ticket.school else "",
            "provider": provider_name,
            "escalated_by": current_user.display_name,
        },
    )
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not any(e.event_type == "escalated" for e in ticket.events):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket não está escalado")
    app_settings = _read_settings()
    provider_name = (app_settings.get("support_provider_name") or "Fornecedor externo").strip()
    db.add(TicketEvent(ticket_id=ticket.id, actor_id=current_user.id, event_type="deescalated", message=f"Ticket resolvido pelo fornecedor ({provider_name})"))
    await db.commit()
    return await ticket_service.get_ticket(db, ticket_id)


@router.post("/{ticket_id}/watchers", response_model=TicketRead)
async def add_watcher(
    ticket_id: int,
    data: WatcherAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    is_creator = ticket.creator_id == current_user.id
    is_staff = current_user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or current_user.is_technician
    if not is_creator and not is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    is_creator = ticket.creator_id == current_user.id
    is_staff = current_user.role in {UserRole.ADMIN, UserRole.TECHNICIAN} or current_user.is_technician
    if not is_creator and not is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if not _can_access_ticket(ticket, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician:
        data.is_internal = False
    comment = await ticket_service.add_comment(db, ticket, data, current_user)

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

    if not data.is_internal:
        recipients = _ticket_update_recipients(ticket, current_user)
        for recipient in recipients:
            await email_service.send_ticket_notification(
                recipient,
                "commented",
                {
                    "id": ticket.id,
                    "title": ticket.title,
                    "author": current_user.display_name,
                    "comment": data.body,
                },
            )
        push_ids = {
            uid for uid in [
                ticket.creator_id,
                ticket.assignee_id,
                *(a.id for a in ticket.assignees),
                *(m.id for m in (ticket.group.members if ticket.group else [])),
                *(w.id for w in ticket.watchers),
            ]
            if uid and uid != current_user.id
        }
        if push_ids:
            asyncio.create_task(push_service.send_push_to_users_bg(
                push_ids,
                f"Nova resposta: {ticket.title}",
                f"{current_user.display_name}: {data.body[:80]}",
                f"/tickets/{ticket.id}",
            ))
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id, Comment.deleted_at.is_(None)))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    comment.ticket = ticket
    updated = await ticket_service.update_comment(db, comment, data.body)
    if not comment.is_internal:
        recipients = _ticket_update_recipients(ticket, current_user)
        for recipient in recipients:
            await email_service.send_ticket_notification(
                recipient,
                "commented",
                {
                    "id": ticket.id,
                    "title": ticket.title,
                    "author": current_user.display_name,
                    "comment": data.body,
                },
            )
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id, Comment.deleted_at.is_(None)))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and not current_user.is_technician and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    comment.ticket = ticket
    await ticket_service.delete_comment(db, comment)


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
