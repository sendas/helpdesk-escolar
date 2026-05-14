from contextlib import asynccontextmanager
import asyncio
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.api.v1.router import router


async def _add_missing_columns(conn) -> None:
    """Add columns and backfill data introduced after initial schema creation."""
    from sqlalchemy import text

    # 1. Add is_escalated if missing
    rows = await conn.execute(text("PRAGMA table_info(tickets)"))
    existing = {row[1] for row in rows}
    if "is_escalated" not in existing:
        await conn.execute(text("ALTER TABLE tickets ADD COLUMN is_escalated BOOLEAN NOT NULL DEFAULT 0"))

    # 2. Backfill: mark tickets that have an 'escalated' event with no later 'deescalated' event
    await conn.execute(text("""
        UPDATE tickets SET is_escalated = 1
        WHERE id IN (
            SELECT ticket_id FROM ticket_events WHERE event_type = 'escalated'
        ) AND id NOT IN (
            SELECT ticket_id FROM ticket_events WHERE event_type = 'deescalated'
        ) AND is_escalated = 0
    """))

    # 3. Reopen tickets closed by erroneous migration scripts (no matching ticket_event)
    await conn.execute(text("""
        UPDATE tickets SET status = 'open'
        WHERE status = 'closed'
        AND id NOT IN (
            SELECT ticket_id FROM ticket_events
            WHERE event_type = 'status_changed' AND new_value = 'closed'
        )
    """))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (no Alembic needed for simple deployments)
    from app.database import engine, Base
    import app.models  # noqa: F401 — registers all models with Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _add_missing_columns(conn)
    from app.database import AsyncSessionLocal
    from app.services.bootstrap import ensure_defaults
    async with AsyncSessionLocal() as db:
        await ensure_defaults(db)
    sync_task = None
    if settings.azure_sync_interval_minutes > 0:
        sync_task = asyncio.create_task(_sync_azure_periodically())
    mail_task = None
    if settings.mail_reply_enabled:
        mail_task = asyncio.create_task(_sync_mail_replies_periodically())
    backup_task = asyncio.create_task(_backup_periodically())
    yield
    if sync_task:
        sync_task.cancel()
    if mail_task:
        mail_task.cancel()
    backup_task.cancel()


async def _sync_azure_periodically() -> None:
    from app.database import AsyncSessionLocal
    from app.services import azure_import

    while True:
        if settings.azure_sync_interval_minutes >= 1440:
            await asyncio.sleep(_seconds_until_next_nightly_sync())
        else:
            await asyncio.sleep(max(settings.azure_sync_interval_minutes, 5) * 60)
        async with AsyncSessionLocal() as db:
            try:
                await azure_import.import_azure_users(db)
            except Exception:
                pass


def _seconds_until_next_nightly_sync() -> float:
    now = datetime.now(ZoneInfo("Europe/Lisbon"))
    target = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return max((target - now).total_seconds(), 60)


async def _sync_mail_replies_periodically() -> None:
    from app.database import AsyncSessionLocal
    from app.services import email_ingest

    interval = max(settings.imap_poll_seconds, 30)
    while True:
        await asyncio.sleep(interval)
        async with AsyncSessionLocal() as db:
            try:
                await email_ingest.sync_inbound_replies(db)
            except Exception:
                pass


async def _backup_periodically() -> None:
    from app.database import AsyncSessionLocal
    from app.services import backup_service

    loop = asyncio.get_event_loop()
    first_run = True
    while True:
        config = backup_service.load_config()
        json_on = config["enabled"]
        zip_on = config.get("full_zip_enabled", False)
        if not json_on and not zip_on:
            await asyncio.sleep(300)
            first_run = True
            continue
        if first_run:
            first_run = False
            if json_on:
                async with AsyncSessionLocal() as db:
                    try:
                        await backup_service.write_backup_auto(db)
                    except Exception:
                        pass
            if zip_on:
                try:
                    await loop.run_in_executor(None, backup_service.write_full_zip_auto)
                except Exception:
                    pass
        await asyncio.sleep(max(config["interval_hours"], 1) * 3600)
        config = backup_service.load_config()
        if config["enabled"]:
            async with AsyncSessionLocal() as db:
                try:
                    await backup_service.write_backup_auto(db)
                except Exception:
                    pass
        if config.get("full_zip_enabled", False):
            try:
                await loop.run_in_executor(None, backup_service.write_full_zip_auto)
            except Exception:
                pass


app = FastAPI(
    title="Teacher Ticket System",
    description="Sistema de tickets para professores autenticados via Active Directory",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.app_secret_key)

@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if _should_log_access(request.url.path):
        try:
            await _record_access(request, response.status_code, int((time.perf_counter() - start) * 1000))
        except Exception:
            pass
    return response

app.include_router(router)
os.makedirs("/app/data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="/app/data/uploads"), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}


def _should_log_access(path: str) -> bool:
    if not path.startswith("/api/"):
        return False
    ignored = (
        "/api/v1/notifications/vapid-public-key",
        "/api/v1/settings/public",
    )
    return not any(path.startswith(prefix) for prefix in ignored)


async def _record_access(request: Request, status_code: int, duration_ms: int) -> None:
    from app.database import AsyncSessionLocal
    from app.models.access_log import AccessLog
    from app.services.jwt_service import decode_token

    user_id = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        payload = decode_token(auth_header.split(" ", 1)[1])
        if payload and payload.get("sub"):
            try:
                user_id = int(payload["sub"])
            except (TypeError, ValueError):
                user_id = None

    user_agent = (request.headers.get("user-agent") or "")[:500]
    forwarded_for = request.headers.get("x-forwarded-for", "")
    ip_address = (forwarded_for.split(",", 1)[0].strip() or (request.client.host if request.client else ""))[:80]
    entry = AccessLog(
        method=request.method[:12],
        path=request.url.path[:300],
        status_code=status_code,
        duration_ms=duration_ms,
        ip_address=ip_address,
        user_agent=user_agent,
        browser=_browser_from_user_agent(user_agent),
        device=_device_from_user_agent(user_agent),
        user_id=user_id,
    )
    async with AsyncSessionLocal() as db:
        db.add(entry)
        await db.commit()


def _browser_from_user_agent(user_agent: str) -> str:
    ua = user_agent.lower()
    if "edg/" in ua:
        return "Edge"
    if "chrome/" in ua or "crios/" in ua:
        return "Chrome"
    if "firefox/" in ua or "fxios/" in ua:
        return "Firefox"
    if "safari/" in ua:
        return "Safari"
    return "Outro"


def _device_from_user_agent(user_agent: str) -> str:
    ua = user_agent.lower()
    if "ipad" in ua or "tablet" in ua:
        return "Tablet"
    if "iphone" in ua or "android" in ua or "mobile" in ua:
        return "Telemóvel"
    return "Computador"
