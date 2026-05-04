from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.ticket import Ticket, Comment, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketUpdate, CommentCreate


async def create_ticket(db: AsyncSession, data: TicketCreate, creator: User) -> Ticket:
    ticket = Ticket(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        school_id=data.school_id,
        priority=data.priority,
        creator_id=creator.id,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return await get_ticket(db, ticket.id)


async def get_ticket(db: AsyncSession, ticket_id: int) -> Ticket | None:
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.creator),
            selectinload(Ticket.assignee),
            selectinload(Ticket.category),
            selectinload(Ticket.school),
            selectinload(Ticket.comments).selectinload(Comment.author),
            selectinload(Ticket.attachments),
        )
    )
    return result.scalar_one_or_none()


async def list_tickets(
    db: AsyncSession,
    user: User,
    page: int = 1,
    size: int = 20,
    status: TicketStatus | None = None,
    category_id: int | None = None,
) -> tuple[list[Ticket], int]:
    query = select(Ticket).options(
        selectinload(Ticket.creator),
        selectinload(Ticket.assignee),
        selectinload(Ticket.category),
        selectinload(Ticket.school),
    )
    if user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN}:
        query = query.where(Ticket.creator_id == user.id)
    if status:
        query = query.where(Ticket.status == status)
    if category_id:
        query = query.where(Ticket.category_id == category_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Ticket.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def update_ticket(db: AsyncSession, ticket: Ticket, data: TicketUpdate) -> Ticket:
    if data.status is not None:
        ticket.status = data.status
    if "assignee_id" in data.model_fields_set:
        ticket.assignee_id = data.assignee_id
        if data.assignee_id is not None and ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED
    if data.priority is not None:
        ticket.priority = data.priority
    ticket.updated_at = datetime.utcnow()
    await db.commit()
    return await get_ticket(db, ticket.id)


async def add_comment(db: AsyncSession, ticket: Ticket, data: CommentCreate, author: User) -> Comment:
    comment = Comment(
        body=data.body,
        is_internal=data.is_internal,
        ticket_id=ticket.id,
        author_id=author.id,
    )
    db.add(comment)
    ticket.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(comment)
    result = await db.execute(
        select(Comment).where(Comment.id == comment.id).options(selectinload(Comment.author))
    )
    return result.scalar_one()
