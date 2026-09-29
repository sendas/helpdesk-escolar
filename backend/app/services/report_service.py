"""Monthly report for the Direção: volume of requests, response times, schools, categories and satisfaction.

Sent by email on the 1st of each month (Configurações → Relatório mensal) and available as a printable page."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.planning import TicketRating
from app.models.school import School
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User

logger = logging.getLogger(__name__)
_LISBON = ZoneInfo("Europe/Lisbon")
_DONE = (TicketStatus.RESOLVED, TicketStatus.CLOSED)
MONTHS_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
             "novembro", "dezembro"]


def previous_month(today: date | None = None) -> tuple[int, int]:
    today = today or datetime.now(_LISBON).date()
    first = today.replace(day=1)
    last_month = first - timedelta(days=1)
    return last_month.year, last_month.month


def _utc_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Start/end of the month in Lisbon time, as naive UTC (how the database stores dates)."""
    start = datetime(year, month, 1, tzinfo=_LISBON)
    end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=_LISBON)
    to_utc = lambda d: d.astimezone(timezone.utc).replace(tzinfo=None)  # noqa: E731
    return to_utc(start), to_utc(end)


async def build_report(db: AsyncSession, year: int, month: int) -> dict:
    start, end = _utc_bounds(year, month)
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_start, prev_end = _utc_bounds(prev_y, prev_m)
    not_demo = Ticket.creator.has(func.coalesce(User.auth_provider, "") != "demo")

    async def count(*where) -> int:
        return (await db.execute(select(func.count()).select_from(Ticket).where(not_demo, *where))).scalar_one()

    created = await count(Ticket.created_at >= start, Ticket.created_at < end)
    created_prev = await count(Ticket.created_at >= prev_start, Ticket.created_at < prev_end)
    resolved = await count(Ticket.status.in_(_DONE), Ticket.resolved_at >= start, Ticket.resolved_at < end)
    open_now = await count(Ticket.status.notin_(_DONE), Ticket.archived_at.is_(None))

    avg_days = (await db.execute(
        select(func.avg(func.julianday(Ticket.resolved_at) - func.julianday(Ticket.created_at)))
        .where(not_demo, Ticket.status.in_(_DONE), Ticket.resolved_at >= start, Ticket.resolved_at < end)
    )).scalar_one()

    by_school = [
        {"name": name or "Sem escola", "count": n}
        for name, n in (await db.execute(
            select(School.name, func.count(Ticket.id)).select_from(Ticket).outerjoin(School, School.id == Ticket.school_id)
            .where(not_demo, Ticket.created_at >= start, Ticket.created_at < end)
            .group_by(School.name).order_by(func.count(Ticket.id).desc())
        )).all()
    ]
    by_category = [
        {"name": name, "count": n}
        for name, n in (await db.execute(
            select(Category.name, func.count(Ticket.id)).join(Category, Category.id == Ticket.category_id)
            .where(not_demo, Ticket.created_at >= start, Ticket.created_at < end)
            .group_by(Category.name).order_by(func.count(Ticket.id).desc()).limit(10)
        )).all()
    ]
    by_technician = [
        {"name": name, "count": n}
        for name, n in (await db.execute(
            select(User.display_name, func.count(Ticket.id)).join(User, User.id == Ticket.assignee_id)
            .where(not_demo, Ticket.status.in_(_DONE), Ticket.resolved_at >= start, Ticket.resolved_at < end)
            .group_by(User.display_name).order_by(func.count(Ticket.id).desc()).limit(10)
        )).all()
    ]
    stars = (await db.execute(
        select(func.avg(TicketRating.stars), func.count(TicketRating.id))
        .where(TicketRating.created_at >= start, TicketRating.created_at < end)
    )).one()

    return {
        "year": year, "month": month, "month_label": f"{MONTHS_PT[month - 1]} de {year}",
        "created": created, "created_prev": created_prev, "created_delta": created - created_prev,
        "resolved": resolved, "open_now": open_now,
        "avg_resolution_hours": round(avg_days * 24, 1) if avg_days is not None else None,
        "by_school": by_school, "by_category": by_category, "by_technician": by_technician,
        "rating_average": round(stars[0], 2) if stars[0] is not None else None, "rating_count": stars[1],
        "generated_at": datetime.now(_LISBON).strftime("%d/%m/%Y %H:%M"),
    }


def render_html(report: dict, org_name: str) -> str:
    from app.services.email_service import jinja_env
    return jinja_env.get_template("monthly_report.html").render(org_name=org_name, **report)


async def send_report(db: AsyncSession, year: int, month: int, recipients: list[str]) -> dict:
    from app.api.v1.settings import _read_settings
    from app.services.email_service import send_html
    report = await build_report(db, year, month)
    html = render_html(report, _read_settings().get("org_name") or "Helpdesk")
    await send_html(recipients, f"[Helpdesk] Relatório de {report['month_label']}", html)
    return report


async def send_due_report(db: AsyncSession) -> bool:
    """On the 1st of the month (from 08:00, or later if the server was off), send last month's report once."""
    from app.api.v1.settings import _read_settings, _update_settings
    s = _read_settings()
    recipients = s.get("report_recipients") or []
    if not s.get("report_enabled") or not recipients:
        return False
    now = datetime.now(_LISBON)
    if now.day == 1 and now.hour < 8:
        return False
    year, month = previous_month(now.date())
    key = f"{year:04d}-{month:02d}"
    if s.get("report_last_sent") == key:
        return False
    await send_report(db, year, month, recipients)
    _update_settings({"report_last_sent": key})
    logger.info("Relatório mensal de %s enviado a %s", key, recipients)
    return True
