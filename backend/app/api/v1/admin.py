from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, require_staff, require_admin
from app.models.user import User
from app.models.ticket import Ticket, Comment, TicketStatus
from app.schemas.ticket import TicketRead, TicketUpdate, PaginatedTickets
from app.services import ticket_service, email_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tickets", response_model=PaginatedTickets)
async def admin_list_tickets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: TicketStatus | None = None,
    category_id: int | None = None,
    school_id: int | None = None,
    assignee_id: int | None = None,
    priority: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    query = select(Ticket).options(
        selectinload(Ticket.creator),
        selectinload(Ticket.assignee),
        selectinload(Ticket.category),
        selectinload(Ticket.school),
    )
    if status:
        query = query.where(Ticket.status == status)
    if category_id:
        query = query.where(Ticket.category_id == category_id)
    if school_id:
        query = query.where(Ticket.school_id == school_id)
    if assignee_id:
        query = query.where(Ticket.assignee_id == assignee_id)
    if priority:
        query = query.where(Ticket.priority == priority)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Ticket.created_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return {"items": items, "total": total, "page": page, "size": size}


@router.patch("/tickets/{ticket_id}", response_model=TicketRead)
async def admin_update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    prev_assignee_id = ticket.assignee_id
    updated = await ticket_service.update_ticket(db, ticket, data)

    await email_service.send_ticket_notification(
        updated.creator.email, "updated",
        {"id": updated.id, "title": updated.title, "status": updated.status.value},
    )
    if data.assignee_id and data.assignee_id != prev_assignee_id and updated.assignee:
        await email_service.send_ticket_notification(
            updated.creator.email, "assigned",
            {"id": updated.id, "title": updated.title, "assignee": updated.assignee.display_name},
        )
    return updated


@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    counts = {}
    for s in TicketStatus:
        result = await db.execute(select(func.count()).select_from(Ticket).where(Ticket.status == s))
        counts[s.value] = result.scalar_one()
    total = (await db.execute(select(func.count()).select_from(Ticket))).scalar_one()

    from app.models.category import Category
    from app.models.user import User as UserModel, UserRole
    from datetime import datetime, timedelta

    # by category
    by_category = []
    cats = (await db.execute(select(Category))).scalars().all()
    for cat in cats:
        c = (await db.execute(select(func.count()).select_from(Ticket).where(Ticket.category_id == cat.id))).scalar_one()
        by_category.append({"name": cat.name, "color": cat.color, "count": c})

    # counts
    user_count = (await db.execute(select(func.count()).select_from(UserModel))).scalar_one()
    category_count = len(cats)
    staff_roles = [UserRole.TECHNICIAN, UserRole.ADMIN]
    staff_count = (await db.execute(
        select(func.count()).select_from(UserModel).where(UserModel.role.in_(staff_roles))
    )).scalar_one()

    # weekly (last 4 weeks)
    weekly = []
    now = datetime.utcnow()
    for i in range(3, -1, -1):
        week_start = now - timedelta(days=(i + 1) * 7)
        week_end = now - timedelta(days=i * 7)
        created = (await db.execute(
            select(func.count()).select_from(Ticket)
            .where(Ticket.created_at >= week_start, Ticket.created_at < week_end)
        )).scalar_one()
        resolved = (await db.execute(
            select(func.count()).select_from(Ticket)
            .where(Ticket.updated_at >= week_start, Ticket.updated_at < week_end,
                   Ticket.status == TicketStatus.RESOLVED)
        )).scalar_one()
        label = f"Sem {4 - i}"
        weekly.append({"week": label, "created": created, "resolved": resolved})

    # by assignee
    staff_users = (await db.execute(
        select(UserModel).where(UserModel.role.in_(staff_roles))
    )).scalars().all()
    by_assignee = []
    for u in staff_users:
        resolved_count = (await db.execute(
            select(func.count()).select_from(Ticket)
            .where(Ticket.assignee_id == u.id, Ticket.status == TicketStatus.RESOLVED)
        )).scalar_one()
        in_progress = (await db.execute(
            select(func.count()).select_from(Ticket)
            .where(Ticket.assignee_id == u.id, Ticket.status == TicketStatus.IN_PROGRESS)
        )).scalar_one()
        by_assignee.append({
            "name": u.display_name, "resolved": resolved_count,
            "in_progress": in_progress, "rating": min(5, max(1, resolved_count // 2 + 1)),
        })

    return {
        "total": total,
        "open": counts.get("open", 0),
        "resolved": counts.get("resolved", 0),
        "by_status": counts,
        "by_category": by_category,
        "weekly": weekly,
        "by_assignee": by_assignee,
        "user_count": user_count,
        "category_count": category_count,
        "staff_count": staff_count,
    }


@router.get("/backup")
async def backup(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    from app.models.school import School
    from app.models.category import Category
    from app.models.user import User as UserModel
    from app.models.ticket import Ticket as TicketModel, Comment as CommentModel, Attachment as AttachmentModel
    import json
    from datetime import datetime

    schools = (await db.execute(select(School))).scalars().all()
    cats = (await db.execute(select(Category))).scalars().all()
    users = (await db.execute(select(UserModel))).scalars().all()
    tickets = (await db.execute(select(TicketModel))).scalars().all()
    comments = (await db.execute(select(CommentModel))).scalars().all()
    attachments = (await db.execute(select(AttachmentModel))).scalars().all()

    def to_dict(obj):
        d = {}
        for col in obj.__table__.columns:
            v = getattr(obj, col.name)
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            elif hasattr(v, "value"):
                v = v.value
            d[col.name] = v
        return d

    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "schools": [to_dict(s) for s in schools],
        "categories": [to_dict(c) for c in cats],
        "users": [to_dict(u) for u in users],
        "tickets": [to_dict(t) for t in tickets],
        "comments": [to_dict(c) for c in comments],
        "attachments": [to_dict(a) for a in attachments],
    }
    from fastapi.responses import JSONResponse
    return JSONResponse(content=data, headers={"Content-Disposition": "attachment; filename=helpdesk-backup.json"})
