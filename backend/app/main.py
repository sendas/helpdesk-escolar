from contextlib import asynccontextmanager
import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.api.v1.router import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


class _HideTokens(logging.Filter):
    """uvicorn's access log prints the full URL; the WebSocket URL carries the session token."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) >= 3 and "token=" in str(record.args[2]):
            args = list(record.args)
            args[2] = re.sub(r"token=[^&\s]+", "token=***", str(args[2]))
            record.args = tuple(args)
        return True


logging.getLogger("uvicorn.access").addFilter(_HideTokens())
logger = logging.getLogger("app.tasks")
_background_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> asyncio.Task:
    """create_task that keeps a reference (unreferenced tasks can be garbage-collected mid-run) and logs failures."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)

    def _done(t: asyncio.Task) -> None:
        _background_tasks.discard(t)
        if not t.cancelled() and t.exception() is not None:
            logger.error("Tarefa em segundo plano falhou", exc_info=t.exception())
    task.add_done_callback(_done)
    return task


async def _add_missing_columns(conn) -> None:
    """Add columns and backfill data introduced after initial schema creation."""
    from sqlalchemy import text

    # 1. Add is_escalated if missing
    rows = await conn.execute(text("PRAGMA table_info(tickets)"))
    existing = {row[1] for row in rows}
    if "is_escalated" not in existing:
        await conn.execute(text("ALTER TABLE tickets ADD COLUMN is_escalated BOOLEAN NOT NULL DEFAULT 0"))

    # 2. Add category warning columns if missing
    rows_cat = await conn.execute(text("PRAGMA table_info(categories)"))
    existing_cat = {row[1] for row in rows_cat}
    if "warning_enabled" not in existing_cat:
        await conn.execute(text("ALTER TABLE categories ADD COLUMN warning_enabled BOOLEAN NOT NULL DEFAULT 0"))
    if "warning_text" not in existing_cat:
        await conn.execute(text("ALTER TABLE categories ADD COLUMN warning_text TEXT"))

    # 3. Backfill: mark tickets that have an 'escalated' event with no later 'deescalated' event
    await conn.execute(text("""
        UPDATE tickets SET is_escalated = 1
        WHERE id IN (
            SELECT ticket_id FROM ticket_events WHERE event_type = 'escalated'
        ) AND id NOT IN (
            SELECT ticket_id FROM ticket_events WHERE event_type = 'deescalated'
        ) AND is_escalated = 0
    """))

    # 5. Per-user list of categories hidden from Painel inicial / Os meus tickets
    rows_u = await conn.execute(text("PRAGMA table_info(users)"))
    if "hidden_category_ids" not in {row[1] for row in rows_u}:
        await conn.execute(text("ALTER TABLE users ADD COLUMN hidden_category_ids VARCHAR(500)"))

    # 6. Reminder date on internal notes
    rows_c = await conn.execute(text("PRAGMA table_info(comments)"))
    existing_c = {row[1] for row in rows_c}
    if "remind_at" not in existing_c:
        await conn.execute(text("ALTER TABLE comments ADD COLUMN remind_at DATETIME"))
    if "reminder_sent_at" not in existing_c:
        await conn.execute(text("ALTER TABLE comments ADD COLUMN reminder_sent_at DATETIME"))
    # 7. Private messages between two people inside a ticket
    if "private_to_id" not in existing_c:
        await conn.execute(text("ALTER TABLE comments ADD COLUMN private_to_id INTEGER REFERENCES users(id)"))

    # 7b. Private messages to several people: existing ones get their single recipient in the new table
    await conn.execute(text("""
        INSERT OR IGNORE INTO comment_private_recipients (comment_id, user_id)
        SELECT id, private_to_id FROM comments WHERE private_to_id IS NOT NULL
    """))

    # 7d. When each ticket was resolved/closed (statistics). Older tickets: the last recorded change to Resolvido/
    # Fechado in their history, otherwise their last update
    rows_t = await conn.execute(text("PRAGMA table_info(tickets)"))
    if "resolved_at" not in {row[1] for row in rows_t}:
        await conn.execute(text("ALTER TABLE tickets ADD COLUMN resolved_at DATETIME"))
        await conn.execute(text("""
            UPDATE tickets SET resolved_at = COALESCE(
                (SELECT MAX(e.created_at) FROM ticket_events e
                 WHERE e.ticket_id = tickets.id
                   AND (e.event_type = 'status_changed'
                        OR e.message LIKE 'Estado alterado para Resolvido%'
                        OR e.message LIKE 'Estado alterado para Fechado%')),
                updated_at)
            WHERE status IN ('RESOLVED', 'CLOSED') AND resolved_at IS NULL
        """))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tickets_resolved_at ON tickets (resolved_at)"))
    await _recompute_resolved_at_once(conn)

    # 7c. Indexes for the columns every ticket page, list and counter filters on
    for name, table, cols in (
        ("ix_comments_ticket_id", "comments", "ticket_id"),
        ("ix_ticket_events_ticket_id", "ticket_events", "ticket_id"),
        ("ix_attachments_ticket_id", "attachments", "ticket_id"),
        ("ix_processed_emails_ticket_id", "processed_emails", "ticket_id"),
        ("ix_tickets_status", "tickets", "status"),
        ("ix_tickets_creator_id", "tickets", "creator_id"),
        ("ix_tickets_assignee_id", "tickets", "assignee_id"),
        ("ix_tickets_category_id", "tickets", "category_id"),
        ("ix_tickets_created_at", "tickets", "created_at"),
        ("ix_tickets_updated_at", "tickets", "updated_at"),
        ("ix_tickets_archived_at", "tickets", "archived_at"),
        ("ix_ticket_watchers_user_id", "ticket_watchers", "user_id"),
        ("ix_ticket_assignees_user_id", "ticket_assignees", "user_id"),
        ("ix_reactions_target", "reactions", "target_type, target_id"),
    ):
        await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})"))

    # 7f. @mentions in replies and notes
    rows_c2 = await conn.execute(text("PRAGMA table_info(comments)"))
    if "mention_ids" not in {row[1] for row in rows_c2}:
        await conn.execute(text("ALTER TABLE comments ADD COLUMN mention_ids VARCHAR(500)"))

    # 7i. Emails to the support company stay in one conversation
    cols_t2 = {row[1] for row in await conn.execute(text("PRAGMA table_info(tickets)"))}
    if "provider_thread_id" not in cols_t2:
        await conn.execute(text("ALTER TABLE tickets ADD COLUMN provider_thread_id VARCHAR(255)"))
    if "provider_ref" not in cols_t2:
        await conn.execute(text("ALTER TABLE tickets ADD COLUMN provider_ref VARCHAR(30)"))

    # 7h. Files attached to one reply: they follow its visibility (private message, internal note)
    rows_a = await conn.execute(text("PRAGMA table_info(attachments)"))
    if "comment_id" not in {row[1] for row in rows_a}:
        await conn.execute(text("ALTER TABLE attachments ADD COLUMN comment_id INTEGER REFERENCES comments(id)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_attachments_comment_id ON attachments (comment_id)"))

    # 7g. Own profile: chosen name, name from the directory, phone
    rows_u4 = await conn.execute(text("PRAGMA table_info(users)"))
    cols_u4 = {row[1] for row in rows_u4}
    if "name_locked" not in cols_u4:
        await conn.execute(text("ALTER TABLE users ADD COLUMN name_locked BOOLEAN NOT NULL DEFAULT 0"))
    if "directory_name" not in cols_u4:
        await conn.execute(text("ALTER TABLE users ADD COLUMN directory_name VARCHAR(200)"))
        await conn.execute(text("UPDATE users SET directory_name = display_name WHERE auth_provider IN ('azure', 'ldap')"))
    if "phone" not in cols_u4:
        await conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(40)"))
    if "news_seen" not in cols_u4:
        await conn.execute(text("ALTER TABLE users ADD COLUMN news_seen INTEGER NOT NULL DEFAULT 0"))

    # 7e. Personal notification preferences
    rows_u3 = await conn.execute(text("PRAGMA table_info(users)"))
    if "notification_prefs" not in {row[1] for row in rows_u3}:
        await conn.execute(text("ALTER TABLE users ADD COLUMN notification_prefs VARCHAR(2000)"))

    # 8. Editable papel per user
    rows_u2 = await conn.execute(text("PRAGMA table_info(users)"))
    if "role_key" not in {row[1] for row in rows_u2}:
        await conn.execute(text("ALTER TABLE users ADD COLUMN role_key VARCHAR(50)"))

    # 4. Add closed_via_email if missing + backfill from email-triggered status events
    if "closed_via_email" not in existing:
        await conn.execute(text("ALTER TABLE tickets ADD COLUMN closed_via_email BOOLEAN NOT NULL DEFAULT 0"))
    await conn.execute(text("""
        UPDATE tickets SET closed_via_email = 1
        WHERE id IN (
            SELECT ticket_id FROM ticket_events
            WHERE event_type = 'status_changed' AND message LIKE '%via email%'
        ) AND closed_via_email = 0
    """))



_DONE_WORDS = ("resolvido", "fechado")
_OPEN_WORDS = ("aberto", "atribuído", "em curso", "a aguardar")


async def _recompute_resolved_at_once(conn) -> None:
    """v2.9.1: resolved_at of older tickets = when they FIRST became resolved/closed (after any reopening), read from
    their history. The first fill used the last change, so a ticket resolved one week and auto-closed later counted
    in the wrong week."""
    from sqlalchemy import text
    from app.api.v1.settings import _read_settings, _update_settings
    done = set(_read_settings().get("settings_migrations") or [])
    if "resolved_at_first_transition" in done:
        return
    rows = (await conn.execute(text("""
        SELECT t.id, t.updated_at, e.created_at, e.event_type, e.message
        FROM tickets t LEFT JOIN ticket_events e ON e.ticket_id = t.id
        WHERE t.status IN ('RESOLVED', 'CLOSED')
        ORDER BY t.id, e.created_at
    """))).all()
    result: dict[int, object] = {}
    fallback: dict[int, object] = {}
    for tid, updated_at, when, kind, message in rows:
        fallback[tid] = updated_at
        text_ = (message or "").lower()
        if when is None or not (kind == "status_changed" or text_.startswith("estado alterado para")):
            continue
        target = text_.split("estado alterado para", 1)[-1] if "estado alterado para" in text_ else text_
        if any(w in target for w in _DONE_WORDS):
            result.setdefault(tid, when)          # first move to resolved/closed
        elif any(w in target for w in _OPEN_WORDS):
            result.pop(tid, None)                 # reopened: the next move counts
    for tid, upd in fallback.items():
        await conn.execute(text("UPDATE tickets SET resolved_at = :w WHERE id = :id"), {"w": result.get(tid, upd), "id": tid})
    done.add("resolved_at_first_transition")
    _update_settings({"settings_migrations": sorted(done)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (no Alembic needed for simple deployments)
    from app.database import engine, Base
    import app.models  # noqa: F401 — registers all models with Base
    from app.services import db_maintenance
    # Copy of the database as the previous version left it, before any migration touches it
    await asyncio.get_running_loop().run_in_executor(None, db_maintenance.startup_snapshot)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _add_missing_columns(conn)
        await db_maintenance.cleanup_orphans(conn)
    from app.database import AsyncSessionLocal
    from app.services.bootstrap import ensure_defaults
    async with AsyncSessionLocal() as db:
        await ensure_defaults(db)
    from app.api.v1.settings import apply_settings_migrations
    apply_settings_migrations()
    from app.services.permissions import ensure_default_roles
    async with AsyncSessionLocal() as db:
        await ensure_default_roles(db)
    sync_task = None
    if settings.azure_sync_interval_minutes > 0:
        sync_task = _spawn(_sync_azure_periodically())
    mail_task = None
    if settings.mail_reply_enabled:
        mail_task = _spawn(_sync_mail_replies_periodically())
    backup_task = _spawn(_backup_periodically())
    inactivity_task = _spawn(_inactivity_check_periodically())
    reminder_task = _spawn(_reminders_periodically())
    support_task = _spawn(_support_timeouts_periodically())
    from app.services import access_log_buffer
    access_task = _spawn(access_log_buffer.run_forever())
    planning_task = _spawn(_planning_and_reports_periodically())
    from app.services.watchdog import Watchdog
    watchdog = Watchdog()
    watchdog.start()
    yield
    watchdog.stop()
    access_task.cancel()
    planning_task.cancel()
    await access_log_buffer.flush()
    support_task.cancel()
    if sync_task:
        sync_task.cancel()
    if mail_task:
        mail_task.cancel()
    backup_task.cancel()
    inactivity_task.cancel()
    reminder_task.cancel()


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
                logger.exception("Sincronização com o Entra ID falhou")


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
                logger.exception("Importação de respostas por email falhou")


async def _inactivity_check_periodically() -> None:
    from app.database import AsyncSessionLocal
    from app.services import inactivity_service

    # First run after 10 minutes (let the app warm up), then every 6 hours
    await asyncio.sleep(600)
    while True:
        async with AsyncSessionLocal() as db:
            try:
                await inactivity_service.run_inactivity_check(db)
            except Exception:
                logger.exception("Verificação de inatividade falhou")
        await asyncio.sleep(6 * 3600)


async def _reminders_periodically() -> None:
    from app.database import AsyncSessionLocal
    from app.services import reminder_service

    await asyncio.sleep(60)
    while True:
        async with AsyncSessionLocal() as db:
            try:
                await reminder_service.send_due_reminders(db)
            except Exception:
                logger.exception("Envio de lembretes falhou")
        await asyncio.sleep(300)


async def _support_timeouts_periodically() -> None:
    from app.database import AsyncSessionLocal
    from app.services import chat_service

    from app.services import teams_service

    rounds = 0
    while True:
        await asyncio.sleep(30)
        rounds += 1
        async with AsyncSessionLocal() as db:
            try:
                await chat_service.expire_waiting(db)
            except Exception:
                logger.exception("Expiração de pedidos de chat falhou")
            if rounds % 20 == 1:  # every 10 minutes
                try:
                    await teams_service.notify_overdue(db)
                except Exception:
                    logger.exception("Aviso de tickets em atraso no Teams falhou")


async def _planning_and_reports_periodically() -> None:
    """Every hour: planned maintenance tickets that are due, and the monthly report on the 1st."""
    from app.database import AsyncSessionLocal
    from app.services import planning_service, report_service

    await asyncio.sleep(120)
    while True:
        async with AsyncSessionLocal() as db:
            try:
                await planning_service.run_due(db)
            except Exception:
                logger.exception("Manutenção planeada falhou")
        async with AsyncSessionLocal() as db:
            try:
                await report_service.send_due_report(db)
            except Exception:
                logger.exception("Relatório mensal falhou")
        await asyncio.sleep(3600)


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
                    except Exception as exc:
                        logger.exception("Backup automático (JSON) falhou")
                        backup_service.record_failure("json", exc)
            if zip_on:
                try:
                    await loop.run_in_executor(None, backup_service.write_full_zip_auto)
                except Exception as exc:
                    logger.exception("Backup automático (ZIP completo) falhou")
                    backup_service.record_failure("zip", exc)
        await asyncio.sleep(max(config["interval_hours"], 1) * 3600)
        config = backup_service.load_config()
        if config["enabled"]:
            async with AsyncSessionLocal() as db:
                try:
                    await backup_service.write_backup_auto(db)
                except Exception as exc:
                    logger.exception("Backup automático (JSON) falhou")
                    backup_service.record_failure("json", exc)
        if config.get("full_zip_enabled", False):
            try:
                await loop.run_in_executor(None, backup_service.write_full_zip_auto)
            except Exception as exc:
                logger.exception("Backup automático (ZIP completo) falhou")
                backup_service.record_failure("zip", exc)


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

_TICKET_PATH = re.compile(r"^/api/v1/(?:admin/)?tickets/(\d+)(?:/|$)")


@app.middleware("http")
async def realtime_ticket_middleware(request: Request, call_next):
    """After any successful change to a ticket, tell the browsers looking at it (see services/realtime.py)."""
    response = await call_next(request)
    if request.method in {"POST", "PATCH", "PUT", "DELETE"} and response.status_code < 400 and request.url.path.startswith("/api/v1/"):
        from app.services import realtime_hooks
        match = _TICKET_PATH.match(request.url.path)
        if match:
            _spawn(realtime_hooks.notify_ticket(int(match.group(1))))
        elif request.url.path.rstrip("/") in {"/api/v1/tickets", "/api/v1/admin/tickets/bulk", "/api/v1/admin/tickets/bulk-action"}:
            _spawn(realtime_hooks.notify_ticket_lists())
    return response


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if _should_log_access(request.url.path):
        try:
            _record_access(request, response.status_code, int((time.perf_counter() - start) * 1000))
        except Exception:
            logger.warning("Registo de acesso falhou", exc_info=True)
    return response

app.include_router(router)
# Only the organisation logo is public; ticket attachments are served by the authenticated download endpoint
os.makedirs("/app/data/uploads/branding", exist_ok=True)
app.mount("/uploads/branding", StaticFiles(directory="/app/data/uploads/branding"), name="branding")


@app.get("/health")
async def health():
    return {"status": "ok"}


def _should_log_access(path: str) -> bool:
    if not path.startswith("/api/"):
        return False
    ignored = (
        "/api/v1/notifications/vapid-public-key",
        "/api/v1/settings/public",
        "/api/v1/realtime/",
    )
    return not any(path.startswith(prefix) for prefix in ignored)


def _record_access(request: Request, status_code: int, duration_ms: int) -> None:
    from app.services import access_log_buffer
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
    # nginx sets X-Real-IP to the address it trusts (see frontend/nginx.conf); X-Forwarded-For can be faked
    ip_address = (request.headers.get("x-real-ip", "").strip() or (request.client.host if request.client else ""))[:80]
    access_log_buffer.add(dict(
        method=request.method[:12],
        path=request.url.path[:300],
        status_code=status_code,
        duration_ms=duration_ms,
        ip_address=ip_address,
        user_agent=user_agent,
        browser=_browser_from_user_agent(user_agent),
        device=_device_from_user_agent(user_agent),
        user_id=user_id,
    ))


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
