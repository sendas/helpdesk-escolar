from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.ticket import TicketStatus
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate, PaginatedTickets, CommentCreate, CommentRead
from app.services import ticket_service, email_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


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
    ticket = await ticket_service.create_ticket(db, data, current_user)
    await email_service.send_ticket_notification(
        current_user.email,
        "created",
        {"id": ticket.id, "title": ticket.title, "category": ticket.category.name, "priority": ticket.priority.value},
    )
    return ticket


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN and ticket.creator_id != current_user.id:
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
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN and ticket.creator_id != current_user.id:
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
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN and ticket.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await ticket_service.add_comment(db, ticket, data, current_user)
