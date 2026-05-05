from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.group import HelpdeskGroup
from app.models.ticket import Ticket, Comment, TicketEvent, TicketRoutingRule, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate, TicketUpdate, CommentCreate


async def create_ticket(db: AsyncSession, data: TicketCreate, creator: User) -> Ticket:
    group_id, assignee_id = await _resolve_route(db, data.category_id, data.school_id)
    ticket = Ticket(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        school_id=data.school_id,
        priority=data.priority,
        creator_id=creator.id,
        creator_email_notifications=data.creator_email_notifications,
        group_id=group_id,
        assignee_id=assignee_id,
        status=TicketStatus.ASSIGNED if group_id or assignee_id else TicketStatus.OPEN,
    )
    if data.watcher_ids:
        watcher_ids = [uid for uid in dict.fromkeys(data.watcher_ids) if uid != creator.id]
        if watcher_ids:
            watchers = (
                await db.execute(
                    select(User).where(User.id.in_(watcher_ids), User.is_active.is_(True))
                )
            ).scalars().all()
            ticket.watchers = list(watchers)
    db.add(ticket)
    db.add(TicketEvent(ticket=ticket, actor_id=creator.id, event_type="created", message="Ticket criado"))
    if ticket.watchers:
        db.add(
            TicketEvent(
                ticket=ticket,
                actor_id=creator.id,
                event_type="watchers_added",
                message=f"Adicionado conhecimento a {len(ticket.watchers)} pessoa(s)",
            )
        )
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
            selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
            selectinload(Ticket.watchers),
            selectinload(Ticket.category),
            selectinload(Ticket.school),
            selectinload(Ticket.comments.and_(Comment.deleted_at.is_(None))).selectinload(Comment.author),
            selectinload(Ticket.attachments),
            selectinload(Ticket.events).selectinload(TicketEvent.actor),
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
        selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
        selectinload(Ticket.watchers),
        selectinload(Ticket.category),
        selectinload(Ticket.school),
    ).where(Ticket.archived_at.is_(None))
    if user.role not in {UserRole.ADMIN, UserRole.TECHNICIAN}:
        query = query.where(or_(Ticket.creator_id == user.id, Ticket.watchers.any(User.id == user.id)))
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
    changes: list[str] = []
    if data.status is not None:
        changes.append(f"Estado alterado para {data.status.value}")
        ticket.status = data.status
    if "assignee_id" in data.model_fields_set:
        ticket.assignee_id = data.assignee_id
        if data.assignee_id is not None and ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED
        changes.append("Responsável atualizado")
    if "group_id" in data.model_fields_set:
        ticket.group_id = data.group_id
        if data.group_id is not None and ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.ASSIGNED
        changes.append("Grupo interno atualizado")
    if data.priority is not None:
        ticket.priority = data.priority
        changes.append(f"Prioridade alterada para {data.priority.value}")
    for message in changes:
        db.add(TicketEvent(ticket_id=ticket.id, event_type="updated", message=message))
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


async def update_comment(db: AsyncSession, comment: Comment, body: str) -> Comment:
    comment.body = body
    comment.updated_at = datetime.utcnow()
    comment.ticket.updated_at = datetime.utcnow()
    db.add(TicketEvent(ticket_id=comment.ticket_id, actor_id=comment.author_id, event_type="comment_edited", message="Resposta editada"))
    await db.commit()
    result = await db.execute(
        select(Comment).where(Comment.id == comment.id).options(selectinload(Comment.author))
    )
    return result.scalar_one()


async def delete_comment(db: AsyncSession, comment: Comment) -> None:
    comment.deleted_at = datetime.utcnow()
    comment.ticket.updated_at = datetime.utcnow()
    db.add(TicketEvent(ticket_id=comment.ticket_id, actor_id=comment.author_id, event_type="comment_deleted", message="Resposta apagada"))
    await db.commit()


async def _resolve_route(db: AsyncSession, category_id: int, school_id: int | None) -> tuple[int | None, int | None]:
    result = await db.execute(
        select(TicketRoutingRule)
        .where(
            (TicketRoutingRule.category_id == category_id) | (TicketRoutingRule.category_id.is_(None)),
            (TicketRoutingRule.school_id == school_id) | (TicketRoutingRule.school_id.is_(None)),
        )
        .order_by(TicketRoutingRule.priority.asc())
    )
    rule = result.scalars().first()
    if not rule:
        return None, None
    return rule.group_id, rule.assignee_id
