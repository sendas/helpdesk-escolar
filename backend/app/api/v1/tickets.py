import os
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.ticket import Attachment, TicketStatus
from app.models.category import Category
from app.models.school import School
from app.schemas.ticket import AttachmentRead, TicketCreate, TicketRead, TicketUpdate, PaginatedTickets, CommentCreate, CommentRead
from app.services import ticket_service, email_service

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
    if not data.is_internal and current_user.id != ticket.creator_id:
        await email_service.send_ticket_notification(
            ticket.creator.email,
            "commented",
            {
                "id": ticket.id,
                "title": ticket.title,
                "author": current_user.display_name,
                "comment": data.body,
            },
        )
    elif current_user.id == ticket.creator_id and ticket.assignee and ticket.assignee.email:
        await email_service.send_ticket_notification(
            ticket.assignee.email,
            "commented",
            {
                "id": ticket.id,
                "title": ticket.title,
                "author": current_user.display_name,
                "comment": data.body,
            },
        )
    return comment
