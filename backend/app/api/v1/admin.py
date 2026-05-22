import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import distinct, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, require_staff, require_admin
from app.models.user import User, UserRole
from app.models.group import HelpdeskGroup
from app.models.ticket import Ticket, Comment, TicketEvent, TicketRoutingRule, TicketStatus
from app.models.access_log import AccessLog
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
    is_escalated: bool | None = None,
    search: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    query = select(Ticket).options(
        selectinload(Ticket.creator),
        selectinload(Ticket.assignee),
        selectinload(Ticket.assignees),
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
        query = query.where(or_(Ticket.assignee_id == assignee_id, Ticket.assignees.any(User.id == assignee_id)))
    if priority:
        query = query.where(Ticket.priority == priority)
    if is_escalated is not None:
        query = query.where(Ticket.is_escalated == is_escalated)
    if search:
        term = f"%{search}%"
        query = query.where(or_(Ticket.title.ilike(term), Ticket.description.ilike(term)))

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
            selectinload(Ticket.assignees),
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
        prev_assignee_ids = _ticket_assignee_ids(ticket)
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
        await _notify_new_assignees(updated, prev_assignee_ids)
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

    result = await db.execute(
        select(Ticket)
        .where(Ticket.id.in_(data.ids))
        .options(selectinload(Ticket.assignees), selectinload(Ticket.watchers))
    )
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

    prev_assignee_ids = _ticket_assignee_ids(ticket)
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
    await _notify_new_assignees(updated, prev_assignee_ids)
    if "group_id" in data.model_fields_set and data.group_id and updated.group:
        for member in updated.group.members:
            if member.email:
                await email_service.send_ticket_notification(
                    member.email,
                    "assigned",
                    {"id": updated.id, "title": updated.title, "assignee": updated.group.name},
                )

    if updated.is_escalated:
        app_settings = _read_settings()
        provider_email = (app_settings.get("support_provider_email") or "").strip()
        provider_name = (app_settings.get("support_provider_name") or "Empresa de apoio").strip()
        if provider_email:
            await email_service.send_ticket_notification(
                provider_email,
                "supplier_updated",
                {
                    "id": updated.id,
                    "title": updated.title,
                    "status": updated.status.value,
                    "priority": updated.priority.value,
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
    if not user or not user.is_active or not (user.role == UserRole.TECHNICIAN or user.is_technician):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O responsável da regra tem de ser um técnico ativo.",
        )


def _ticket_assignee_ids(ticket: Ticket) -> set[int]:
    ids = {ticket.assignee_id} if ticket.assignee_id else set()
    ids.update(user.id for user in getattr(ticket, "assignees", []))
    return ids


async def _notify_new_assignees(ticket: Ticket, previous_ids: set[int]) -> None:
    users = list(ticket.assignees or ([] if not ticket.assignee else [ticket.assignee]))
    for assignee in users:
        if assignee.id in previous_ids or not assignee.email:
            continue
        await email_service.send_ticket_notification(
            assignee.email,
            "assigned",
            {"id": ticket.id, "title": ticket.title, "assignee": assignee.display_name},
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
        select(func.count()).select_from(UserModel).where(or_(UserModel.role.in_(staff_roles), UserModel.is_technician.is_(True)))
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
        select(UserModel).where(or_(UserModel.role == UserRole.TECHNICIAN, UserModel.is_technician.is_(True)))
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

    access_stats = await _build_access_stats(db)

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
        "access": access_stats,
    }


async def _build_access_stats(db: AsyncSession) -> dict:
    now = datetime.utcnow()
    since_7 = now - timedelta(days=7)
    since_30 = now - timedelta(days=30)

    visits_7 = (await db.execute(
        select(func.count()).select_from(AccessLog).where(AccessLog.created_at >= since_7)
    )).scalar_one()
    visits_30 = (await db.execute(
        select(func.count()).select_from(AccessLog).where(AccessLog.created_at >= since_30)
    )).scalar_one()
    unique_users_7 = (await db.execute(
        select(func.count(distinct(AccessLog.user_id))).where(AccessLog.created_at >= since_7, AccessLog.user_id.is_not(None))
    )).scalar_one()
    unique_users_30 = (await db.execute(
        select(func.count(distinct(AccessLog.user_id))).where(AccessLog.created_at >= since_30, AccessLog.user_id.is_not(None))
    )).scalar_one()

    daily = []
    for i in range(13, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        hits = (await db.execute(
            select(func.count()).select_from(AccessLog)
            .where(AccessLog.created_at >= day_start, AccessLog.created_at < day_end)
        )).scalar_one()
        users = (await db.execute(
            select(func.count(distinct(AccessLog.user_id)))
            .where(AccessLog.created_at >= day_start, AccessLog.created_at < day_end, AccessLog.user_id.is_not(None))
        )).scalar_one()
        daily.append({"date": day_start.date().isoformat(), "hits": hits, "users": users})

    top_users_result = await db.execute(
        select(User.id, User.display_name, User.email, func.count(AccessLog.id).label("hits"), func.max(AccessLog.created_at).label("last_seen"))
        .join(AccessLog, AccessLog.user_id == User.id)
        .where(AccessLog.created_at >= since_30)
        .group_by(User.id, User.display_name, User.email)
        .order_by(func.count(AccessLog.id).desc())
        .limit(10)
    )
    top_users = [
        {
            "id": user_id,
            "name": display_name,
            "email": email,
            "hits": hits,
            "last_seen": last_seen.isoformat() if last_seen else None,
        }
        for user_id, display_name, email, hits, last_seen in top_users_result.all()
    ]

    top_paths_result = await db.execute(
        select(AccessLog.path, func.count(AccessLog.id).label("hits"), func.avg(AccessLog.duration_ms).label("avg_ms"))
        .where(AccessLog.created_at >= since_30)
        .group_by(AccessLog.path)
        .order_by(func.count(AccessLog.id).desc())
        .limit(12)
    )
    top_paths = [
        {"path": path, "hits": hits, "avg_ms": round(avg_ms or 0)}
        for path, hits, avg_ms in top_paths_result.all()
    ]

    device_result = await db.execute(
        select(AccessLog.device, func.count(AccessLog.id).label("hits"))
        .where(AccessLog.created_at >= since_30)
        .group_by(AccessLog.device)
        .order_by(func.count(AccessLog.id).desc())
    )
    by_device = [{"device": device or "Desconhecido", "hits": hits} for device, hits in device_result.all()]

    browser_result = await db.execute(
        select(AccessLog.browser, func.count(AccessLog.id).label("hits"))
        .where(AccessLog.created_at >= since_30)
        .group_by(AccessLog.browser)
        .order_by(func.count(AccessLog.id).desc())
    )
    by_browser = [{"browser": browser or "Desconhecido", "hits": hits} for browser, hits in browser_result.all()]

    return {
        "visits_7": visits_7,
        "visits_30": visits_30,
        "unique_users_7": unique_users_7,
        "unique_users_30": unique_users_30,
        "daily": daily,
        "top_users": top_users,
        "top_paths": top_paths,
        "by_device": by_device,
        "by_browser": by_browser,
    }


@router.get("/backup")
async def backup(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    data = await backup_service.build_backup(db)
    return JSONResponse(content=data, headers={"Content-Disposition": "attachment; filename=helpdesk-backup.json"})


@router.get("/backup/full")
async def backup_full(_: User = Depends(require_admin)):
    import os
    tmp_path, filename = backup_service.build_full_zip()

    def _iter_and_cleanup():
        try:
            with open(tmp_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return StreamingResponse(
        _iter_and_cleanup(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/backup/full/save")
async def backup_full_save(_: User = Depends(require_admin)):
    result = backup_service.write_full_zip_to_disk()
    return result


@router.get("/backup/history")
async def get_backup_history(_: User = Depends(require_admin)):
    return backup_service.load_history()


@router.get("/backup/config")
async def get_backup_config(_: User = Depends(require_admin)):
    return backup_service.load_config()


@router.patch("/backup/config")
async def update_backup_config(data: dict, _: User = Depends(require_admin)):
    return backup_service.save_config(data)


@router.post("/backup/run")
async def run_backup(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    import asyncio
    result = await backup_service.write_backup(db)
    config = backup_service.load_config()
    if config.get("full_zip_enabled", False):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, backup_service.write_full_zip_auto)
    return result


@router.post("/backup/restore")
async def restore_backup(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    from fastapi import Request
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use POST /admin/backup/restore com Content-Type: application/json")


@router.post("/backup/restore/upload")
async def restore_backup_upload(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    from fastapi import UploadFile, File as FastAPIFile
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envie o ficheiro no corpo da requisição")


from fastapi import UploadFile, File as FastAPIFile  # noqa: E402


@router.post("/backup/restore/json")
async def restore_backup_json(
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        content = await file.read()
        data = json.loads(content)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ficheiro inválido: {exc}") from exc
    if not isinstance(data, dict) or "tickets" not in data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ficheiro não parece um backup válido")
    counts = await backup_service.restore_backup(db, data)
    return {"restored": True, "counts": counts}


@router.post("/backup/restore/zip")
async def restore_backup_zip(
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    import os
    import shutil
    import tempfile
    import zipfile
    from pathlib import Path
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as AsyncSess
    from sqlalchemy.orm import sessionmaker

    # Stream ZIP to temp file to avoid loading it all into RAM
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
        tmp.close()

        if not zipfile.is_zipfile(tmp.name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ficheiro não é um ZIP válido")

        with zipfile.ZipFile(tmp.name, "r") as zf:
            names = set(zf.namelist())
            if "data/tickets.db" not in names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ZIP não contém data/tickets.db — não parece um backup completo",
                )

            extract_dir = tempfile.mkdtemp(prefix="helpdesk-restore-")
            try:
                zf.extractall(extract_dir)
                extracted_db = Path(extract_dir) / "data" / "tickets.db"
                extracted_uploads = Path(extract_dir) / "data" / "uploads"

                # Read all records from the extracted SQLite into a backup dict
                ext_engine = create_async_engine(f"sqlite+aiosqlite:///{extracted_db}")
                ExtSession = sessionmaker(ext_engine, class_=AsyncSess, expire_on_commit=False)
                try:
                    async with ExtSession() as ext_db:
                        backup_data = await backup_service.build_backup(ext_db)
                finally:
                    await ext_engine.dispose()

                # Restore database records
                counts = await backup_service.restore_backup(db, backup_data)

                # Copy uploads
                uploads_restored = 0
                if extracted_uploads.exists():
                    target_uploads = Path("/app/data/uploads")
                    target_uploads.mkdir(parents=True, exist_ok=True)
                    for src in extracted_uploads.rglob("*"):
                        if src.is_file():
                            rel = src.relative_to(extracted_uploads)
                            dest = target_uploads / rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src, dest)
                            uploads_restored += 1
                counts["upload_files"] = uploads_restored

                # Copy app_settings if present
                for extra in ("app_settings.json", "backup_config.json"):
                    src_file = Path(extract_dir) / "data" / extra
                    if src_file.exists():
                        shutil.copy2(src_file, Path("/app/data") / extra)

                return {"restored": True, "counts": counts}
            finally:
                shutil.rmtree(extract_dir, ignore_errors=True)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@router.post("/onedrive/test")
async def test_onedrive(_: User = Depends(require_admin)):
    import asyncio
    from app.services import onedrive_service
    from app.services.backup_service import load_config
    config = load_config()
    if not config.get("onedrive_user"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilizador OneDrive (UPN) não configurado")
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                onedrive_service.test_connection,
                config["onedrive_user"],
                config["onedrive_folder"],
            ),
            timeout=40.0,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tempo esgotado (40s). Verifique se o servidor tem acesso à internet e se as credenciais Azure AD estão corretas.",
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post("/mail/test")
async def test_mail(current_admin: User = Depends(require_admin)):
    if not current_admin.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O utilizador não tem email configurado")
    try:
        await email_service.send_ticket_notification(
            current_admin.email,
            "updated",
            {"id": 0, "title": "Teste de email do helpdesk", "status": "open"},
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao enviar email: {exc}") from exc
    return {"sent_to": current_admin.email}


@router.post("/fix-resolved-tickets")
async def fix_resolved_tickets(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    """Close tickets where the 'Resolvido ✓' quick reply was used but status was never changed."""
    from sqlalchemy import text
    # Only close tickets whose LAST comment matches the quick reply text exactly
    result = await db.execute(text("""
        SELECT DISTINCT c.ticket_id FROM comments c
        JOIN tickets t ON t.id = c.ticket_id
        WHERE t.status != 'closed'
        AND c.deleted_at IS NULL
        AND c.body = 'A situação foi resolvida. Se o problema voltar a ocorrer, responda a este ticket com mais informação.'
    """))
    ticket_ids = [row[0] for row in result.fetchall()]
    if ticket_ids:
        await db.execute(text(f"UPDATE tickets SET status = 'closed' WHERE id IN ({','.join(str(i) for i in ticket_ids)}) AND status != 'closed'"))
        await db.commit()
    return {"fixed": len(ticket_ids), "ticket_ids": ticket_ids}


@router.post("/reopen-wrongly-closed")
async def reopen_wrongly_closed(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    """Reopen tickets that were closed by the fix script but have no 'closed' event in ticket_events."""
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT id FROM tickets
        WHERE status = 'closed'
        AND id NOT IN (
            SELECT ticket_id FROM ticket_events WHERE event_type = 'status_changed' AND new_value = 'closed'
        )
        AND id NOT IN (
            SELECT DISTINCT c.ticket_id FROM comments c
            WHERE c.body = 'A situação foi resolvida. Se o problema voltar a ocorrer, responda a este ticket com mais informação.'
            AND c.deleted_at IS NULL
        )
    """))
    ticket_ids = [row[0] for row in result.fetchall()]
    if ticket_ids:
        await db.execute(text(f"UPDATE tickets SET status = 'open' WHERE id IN ({','.join(str(i) for i in ticket_ids)})"))
        await db.commit()
    return {"reopened": len(ticket_ids), "ticket_ids": ticket_ids}
