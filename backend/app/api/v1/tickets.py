import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Attachment, Comment, TicketEvent, TicketStatus
from app.models.category import Category
from app.models.school import School
from app.schemas.ticket import AttachmentRead, TicketCreate, TicketRead, TicketUpdate, PaginatedTickets, CommentCreate, CommentRead, CommentUpdate
from app.services import ticket_service, email_service
from app.api.v1.settings import _read_settings
from app.config import settings

router = APIRouter(prefix="/tickets", tags=["tickets"])

UPLOAD_DIR = "/app/data/uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "application/pdf"}


@router.get("", response_model=PaginatedTickets)
async def list_tickets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: TicketStatus | None = None,
    category_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await ticket_service.list_tickets(db, current_user, page, size, status, category_id)
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
    await email_service.send_ticket_notification(
        current_user.email,
        "created",
        {"id": ticket.id, "title": ticket.title, "category": ticket.category.name, "priority": ticket.priority.value},
    )
    if ticket.category.email_to:
        await email_service.send_ticket_notification(
            ticket.category.email_to,
            "created",
            {
                "id": ticket.id,
                "title": ticket.title,
                "category": ticket.category.name,
                "priority": ticket.priority.value,
                "requester": current_user.display_name,
                "school": ticket.school.name if ticket.school else "",
            },
        )
    if ticket.assignee and ticket.assignee.email:
        await email_service.send_ticket_notification(
            ticket.assignee.email,
            "assigned",
            {"id": ticket.id, "title": ticket.title, "assignee": ticket.assignee.display_name},
        )
    if ticket.group:
        for member in ticket.group.members:
            if member.email and member.email != current_user.email:
                await email_service.send_ticket_notification(
                    member.email,
                    "assigned",
                    {"id": ticket.id, "title": ticket.title, "assignee": ticket.group.name},
                )
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
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and ticket.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido. Use PNG, JPG ou PDF.")

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
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and ticket.creator_id != current_user.id:
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
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and ticket.creator_id != current_user.id:
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
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and ticket.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    updated = await ticket_service.update_ticket(db, ticket, data)
    await email_service.send_ticket_notification(
        ticket.creator.email,
        "updated",
        {"id": updated.id, "title": updated.title, "status": updated.status.value},
    )
    return updated


@router.post("/{ticket_id}/escalate", response_model=TicketRead)
async def escalate_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN}:
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
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and ticket.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    comment = await ticket_service.add_comment(db, ticket, data, current_user)
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
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and comment.author_id != current_user.id:
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
    if current_user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN} and comment.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    comment.ticket = ticket
    await ticket_service.delete_comment(db, comment)


def _ticket_update_recipients(ticket, current_user: User) -> set[str]:
    recipients: set[str] = set()
    if current_user.id != ticket.creator_id and ticket.creator.email:
        recipients.add(ticket.creator.email)
    if ticket.assignee and ticket.assignee.email and current_user.id != ticket.assignee_id:
        recipients.add(ticket.assignee.email)
    if ticket.group:
        for member in ticket.group.members:
            if member.email and member.id != current_user.id:
                recipients.add(member.email)
    if ticket.category.email_to:
        recipients.add(ticket.category.email_to)
    return recipients
