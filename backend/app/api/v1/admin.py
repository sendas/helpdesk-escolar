from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, require_staff, require_admin
from app.models.user import User, UserRole
from app.models.group import HelpdeskGroup
from app.models.ticket import Ticket, Comment, TicketEvent, TicketRoutingRule, TicketStatus
from app.schemas.ticket import TicketBulkAction, TicketBulkUpdate, TicketRead, TicketUpdate, PaginatedTickets, TicketRoutingRuleCreate, TicketRoutingRuleRead, TicketRoutingRuleUpdate
from app.services import ticket_service, email_service, email_ingest, backup_service
from app.api.v1.settings import _read_settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/routing-rules", response_model=list[TicketRoutingRuleRead])
async def list_routing_rules(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    result = await db.execute(
        select(TicketRoutingRule)
        .options(
            selectinload(TicketRoutingRule.category),
            selectinload(TicketRoutingRule.school),
            selectinload(TicketRoutingRule.group).selectinload(HelpdeskGroup.members),
            selectinload(TicketRoutingRule.assignee),
        )
        .order_by(TicketRoutingRule.priority.asc())
    )
    return result.scalars().all()


@router.post("/routing-rules", response_model=TicketRoutingRuleRead, status_code=status.HTTP_201_CREATED)
async def create_routing_rule(data: TicketRoutingRuleCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    await _validate_routing_assignee(db, data.assignee_id)
    rule = TicketRoutingRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    result = await db.execute(
        select(TicketRoutingRule)
        .where(TicketRoutingRule.id == rule.id)
        .options(selectinload(TicketRoutingRule.category), selectinload(TicketRoutingRule.school), selectinload(TicketRoutingRule.group), selectinload(TicketRoutingRule.assignee))
    )
    return result.scalar_one()


@router.patch("/routing-rules/{rule_id}", response_model=TicketRoutingRuleRead)
async def update_routing_rule(rule_id: int, data: TicketRoutingRuleUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    rule = (await db.execute(select(TicketRoutingRule).where(TicketRoutingRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing rule not found")
    if "assignee_id" in data.model_fields_set:
        await _validate_routing_assignee(db, data.assignee_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    result = await db.execute(
        select(TicketRoutingRule)
        .where(TicketRoutingRule.id == rule.id)
        .options(selectinload(TicketRoutingRule.category), selectinload(TicketRoutingRule.school), selectinload(TicketRoutingRule.group), selectinload(TicketRoutingRule.assignee))
    )
    return result.scalar_one()


@router.delete("/routing-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_rule(rule_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    rule = (await db.execute(select(TicketRoutingRule).where(TicketRoutingRule.id == rule_id))).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing rule not found")
    await db.delete(rule)
    await db.commit()


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
        selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
        selectinload(Ticket.watchers),
        selectinload(Ticket.category),
        selectinload(Ticket.school),
    ).where(Ticket.archived_at.is_(None))
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


@router.patch("/tickets/bulk", response_model=list[TicketRead])
async def admin_bulk_update_tickets(
    data: TicketBulkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    if not data.ids:
        return []

    result = await db.execute(
        select(Ticket)
        .where(Ticket.id.in_(data.ids))
        .options(
            selectinload(Ticket.creator),
            selectinload(Ticket.assignee),
            selectinload(Ticket.group).selectinload(HelpdeskGroup.members),
            selectinload(Ticket.watchers),
            selectinload(Ticket.category),
            selectinload(Ticket.school),
            selectinload(Ticket.comments).selectinload(Comment.author),
            selectinload(Ticket.attachments),
        )
    )
    tickets = result.scalars().all()
    updated_tickets = []
    only_email_preference = data.model_fields_set == {"ids", "creator_email_notifications"}
    for ticket in tickets:
        prev_assignee_id = ticket.assignee_id
        try:
            updated = await ticket_service.update_ticket(db, ticket, data)
        except ticket_service.TicketValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        updated_tickets.append(updated)
        if only_email_preference:
            continue
        if updated.creator_email_notifications:
            await email_service.send_ticket_notification(
                updated.creator.email, "updated",
                {"id": updated.id, "title": updated.title, "status": updated.status.value},
            )
        for watcher in updated.watchers:
            if watcher.email:
                await email_service.send_ticket_notification(
                    watcher.email,
                    "updated",
                    {"id": updated.id, "title": updated.title, "status": updated.status.value},
                )
        if data.assignee_id and data.assignee_id != prev_assignee_id and updated.assignee:
            await email_service.send_ticket_notification(
                updated.assignee.email,
                "assigned",
                {"id": updated.id, "title": updated.title, "assignee": updated.assignee.display_name},
            )
        if "group_id" in data.model_fields_set and data.group_id and updated.group:
            for member in updated.group.members:
                if member.email:
                    await email_service.send_ticket_notification(
                        member.email,
                        "assigned",
                        {"id": updated.id, "title": updated.title, "assignee": updated.group.name},
                    )
    return updated_tickets


@router.post("/tickets/bulk-action")
async def admin_bulk_action_tickets(
    data: TicketBulkAction,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if not data.ids:
        return {"affected": 0}
    if data.action not in {"archive", "delete"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported bulk action")

    result = await db.execute(select(Ticket).where(Ticket.id.in_(data.ids)))
    tickets = result.scalars().all()
    now = datetime.utcnow()
    affected = 0

    for ticket in tickets:
        if data.action == "archive":
            if ticket.archived_at is None:
                ticket.archived_at = now
                ticket.updated_at = now
                db.add(TicketEvent(ticket_id=ticket.id, actor_id=actor.id, event_type="archived", message="Ticket arquivado"))
                affected += 1
        else:
            await db.delete(ticket)
            affected += 1

    await db.commit()
    return {"affected": affected}


@router.patch("/tickets/{ticket_id}", response_model=TicketRead)
async def admin_update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_staff: User = Depends(require_staff),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    prev_assignee_id = ticket.assignee_id
    only_email_preference = data.model_fields_set == {"creator_email_notifications"}
    content_changed = bool(data.model_fields_set & {"title", "description"})
    try:
        updated = await ticket_service.update_ticket(db, ticket, data)
    except ticket_service.TicketValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if only_email_preference:
        return updated

    notif_type = "content_updated" if content_changed else "updated"
    base_payload = {"id": updated.id, "title": updated.title, "status": updated.status.value}
    if content_changed:
        base_payload["editor"] = current_staff.display_name

    if updated.creator_email_notifications:
        await email_service.send_ticket_notification(updated.creator.email, notif_type, base_payload)
    for watcher in updated.watchers:
        if watcher.email:
            await email_service.send_ticket_notification(watcher.email, notif_type, base_payload)
    if data.assignee_id and data.assignee_id != prev_assignee_id and updated.assignee:
        await email_service.send_ticket_notification(
            updated.assignee.email,
            "assigned",
            {"id": updated.id, "title": updated.title, "assignee": updated.assignee.display_name},
        )
    if "group_id" in data.model_fields_set and data.group_id and updated.group:
        for member in updated.group.members:
            if member.email:
                await email_service.send_ticket_notification(
                    member.email,
                    "assigned",
                    {"id": updated.id, "title": updated.title, "assignee": updated.group.name},
                )

    if content_changed and any(e.event_type == "escalated" for e in updated.events):
        app_settings = _read_settings()
        provider_email = app_settings.get("support_provider_email", "")
        provider_name = app_settings.get("support_provider_name", "Fornecedor externo")
        if provider_email:
            await email_service.send_ticket_notification(
                provider_email,
                "supplier_updated",
                {
                    "id": updated.id,
                    "title": updated.title,
                    "status": updated.status.value,
                    "priority": updated.priority,
                    "description": updated.description,
                    "editor": current_staff.display_name,
                    "provider": provider_name,
                },
            )

    return updated


async def _validate_routing_assignee(db: AsyncSession, assignee_id: int | None) -> None:
    if assignee_id is None:
        return
    result = await db.execute(select(User).where(User.id == assignee_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.role != UserRole.TECHNICIAN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O responsável da regra tem de ser um técnico ativo.",
        )


@router.post("/mail/sync")
async def admin_sync_mail_replies(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await email_ingest.sync_inbound_replies(db, limit=50)


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
    data = await backup_service.build_backup(db)
    return JSONResponse(content=data, headers={"Content-Disposition": "attachment; filename=helpdesk-backup.json"})


@router.get("/backup/config")
async def get_backup_config(_: User = Depends(require_admin)):
    return backup_service.load_config()


@router.patch("/backup/config")
async def update_backup_config(data: dict, _: User = Depends(require_admin)):
    return backup_service.save_config(data)


@router.post("/backup/run")
async def run_backup(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    return await backup_service.write_backup(db)
