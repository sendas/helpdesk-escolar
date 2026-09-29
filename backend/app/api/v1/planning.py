"""Planned maintenance (recurring tickets), managed by the support team."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_perm
from app.models.planning import ScheduledTicket
from app.models.user import User
from app.services import planning_service

router = APIRouter(prefix="/planning", tags=["planning"])


class PlanIn(BaseModel):
    title: str
    description: str = ""
    category_id: int
    school_id: int
    priority: str = "medium"
    assignee_id: int | None = None
    frequency: str = "monthly"
    next_run: date
    active: bool = True


def _out(p: ScheduledTicket) -> dict:
    return {
        "id": p.id, "title": p.title, "description": p.description, "category_id": p.category_id,
        "category": p.category.name if p.category else None, "school_id": p.school_id,
        "school": p.school.name if p.school else None, "priority": p.priority, "assignee_id": p.assignee_id,
        "assignee": p.assignee.display_name if p.assignee else None, "frequency": p.frequency,
        "frequency_label": planning_service.FREQUENCIES.get(p.frequency, p.frequency),
        "next_run": p.next_run.isoformat(), "active": p.active, "last_ticket_id": p.last_ticket_id,
        "last_run_at": p.last_run_at.isoformat() if p.last_run_at else None,
    }


def _check(data: PlanIn) -> None:
    if not data.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indique o assunto do ticket.")
    if data.frequency not in planning_service.FREQUENCIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Frequência inválida.")
    if data.priority not in {"low", "medium", "high", "urgent"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prioridade inválida.")


@router.get("")
async def list_plans(db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("tickets.manage"))):
    rows = (await db.execute(select(ScheduledTicket).order_by(ScheduledTicket.next_run))).scalars().all()
    return {"items": [_out(p) for p in rows], "frequencies": planning_service.FREQUENCIES}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_plan(data: PlanIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_perm("tickets.manage"))):
    _check(data)
    plan = ScheduledTicket(**{**data.model_dump(), "title": data.title.strip()}, created_by_id=user.id)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _out(plan)


@router.put("/{plan_id}")
async def update_plan(plan_id: int, data: PlanIn, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("tickets.manage"))):
    _check(data)
    plan = await db.get(ScheduledTicket, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada.")
    for k, v in data.model_dump().items():
        setattr(plan, k, v.strip() if k == "title" else v)
    await db.commit()
    await db.refresh(plan)
    return _out(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("tickets.manage"))):
    plan = await db.get(ScheduledTicket, plan_id)
    if plan:
        await db.delete(plan)
        await db.commit()


@router.post("/{plan_id}/run")
async def run_plan_now(plan_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(require_perm("tickets.manage"))):
    """Create this maintenance ticket now (the next scheduled date stays as it is)."""
    plan = await db.get(ScheduledTicket, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manutenção não encontrada.")
    try:
        ticket = await planning_service.create_ticket_now(db, plan, user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ticket_id": ticket.id}
