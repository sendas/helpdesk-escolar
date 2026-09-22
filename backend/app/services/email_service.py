import asyncio
import os
import logging
from collections import defaultdict
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jinja2 import Environment, FileSystemLoader
from app.config import settings

_templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
logger = logging.getLogger(__name__)

jinja_env = Environment(loader=FileSystemLoader(_templates_dir))

# Notification digest: several updates to the same ticket, addressed to the same
# recipient, within a short window get merged into a single email instead of one
# per change (e.g. add comment + resolve + close in quick succession).
_DIGEST_WINDOW_SECONDS = settings.mail_digest_window_seconds
_pending: dict[tuple[str, int], list[dict]] = defaultdict(list)
_flush_tasks: dict[tuple[str, int], "asyncio.Task"] = {}


def _get_conf() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        USE_CREDENTIALS=bool(settings.mail_username),
        SUPPRESS_SEND=settings.mail_suppress_send,
    )


def build_ticket_url(ticket_id: int | str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/tickets/{ticket_id}"


_STATUS_PT: dict[str, str] = {
    "open": "Aberto",
    "assigned": "Atribuído",
    "in_progress": "Em Curso",
    "waiting_user": "A aguardar utilizador",
    "resolved": "Resolvido",
    "closed": "Fechado",
}
_PRIORITY_PT: dict[str, str] = {
    "low": "Baixa",
    "medium": "Média",
    "high": "Alta",
    "urgent": "Urgente",
}


async def send_suggestion_notification(recipients: list[str], suggestion_data: dict) -> None:
    if not settings.mail_server or not recipients:
        return
    try:
        template = jinja_env.get_template("suggestion_received.html")
        html_body = template.render(**suggestion_data)
    except Exception as exc:
        logger.warning("Email template error for suggestion: %s", exc)
        return
    try:
        message = MessageSchema(
            subject=f"[Helpdesk] Nova sugestão de {suggestion_data.get('author_name', 'utilizador')}",
            recipients=recipients,
            body=html_body,
            subtype=MessageType.html,
        )
        fm = FastMail(_get_conf())
        await fm.send_message(message)
        logger.info("Suggestion notification sent to %s", recipients)
    except Exception as exc:
        logger.warning("Suggestion notification failed: %s", exc)


def _normalize_ticket_data(ticket_data: dict) -> dict:
    ticket_data = dict(ticket_data)
    if ticket_data.get("id") and not ticket_data.get("ticket_url"):
        ticket_data["ticket_url"] = build_ticket_url(ticket_data["id"])
    if "status" in ticket_data:
        ticket_data["status"] = _STATUS_PT.get(str(ticket_data["status"]), str(ticket_data["status"]))
    if "priority" in ticket_data:
        ticket_data["priority"] = _PRIORITY_PT.get(str(ticket_data["priority"]), str(ticket_data["priority"]))
    return ticket_data


async def send_ticket_notification(to_email: str, event: str, ticket_data: dict) -> None:
    if not settings.mail_server:
        return
    ticket_data = _normalize_ticket_data(ticket_data)
    ticket_id = ticket_data.get("id")

    if not ticket_id or _DIGEST_WINDOW_SECONDS <= 0:
        await _send_single(to_email, event, ticket_data)
        return

    key = (to_email.strip().lower(), int(ticket_id))
    _pending[key].append({"event": event, "data": ticket_data})

    existing = _flush_tasks.get(key)
    if existing and not existing.done():
        existing.cancel()
    _flush_tasks[key] = asyncio.create_task(_debounced_flush(key, to_email))


async def _debounced_flush(key: tuple[str, int], to_email: str) -> None:
    try:
        await asyncio.sleep(_DIGEST_WINDOW_SECONDS)
    except asyncio.CancelledError:
        return
    events = _pending.pop(key, [])
    _flush_tasks.pop(key, None)
    if not events:
        return
    if len(events) == 1:
        await _send_single(to_email, events[0]["event"], events[0]["data"])
    else:
        await _send_digest(to_email, events)


async def _send_single(to_email: str, event: str, ticket_data: dict) -> None:
    try:
        template = jinja_env.get_template(f"ticket_{event}.html")
        html_body = template.render(**ticket_data)
    except Exception as exc:
        logger.warning("Email template error for event %s: %s", event, exc)
        return

    try:
        message = MessageSchema(
            subject=f"[Ticket #{ticket_data.get('id')}] {ticket_data.get('title')} - {event.replace('_', ' ').title()}",
            recipients=[to_email],
            body=html_body,
            subtype=MessageType.html,
            headers={"Reply-To": settings.mail_from},
        )
        fm = FastMail(_get_conf())
        await fm.send_message(message)
        logger.info("Email notification sent to %s for ticket %s (%s)", to_email, ticket_data.get("id"), event)
    except Exception as exc:
        logger.warning("Email notification failed to %s for ticket %s (%s): %s", to_email, ticket_data.get("id"), event, exc)


def _event_summary_line(event: str, data: dict) -> str:
    if event in ("commented", "supplier_comment"):
        author = data.get("author") or data.get("provider_name") or ""
        comment = (data.get("comment") or "").strip().replace("\n", " ")
        if len(comment) > 240:
            comment = comment[:240] + "…"
        return f"Resposta de {author}: {comment}" if author else f"Resposta: {comment}"
    if event == "content_updated":
        editor = data.get("editor")
        return f"Assunto/descrição alterados{' por ' + editor if editor else ''}"
    if event in ("updated", "supplier_updated"):
        status = data.get("status")
        return f"Ticket atualizado (estado: {status})" if status else "Ticket atualizado"
    if event == "assigned":
        return f"Atribuído a: {data.get('assignee', '')}"
    if event == "escalated":
        return "Escalado para a empresa de apoio informático"
    if event == "created":
        return "Ticket criado"
    return event.replace("_", " ").capitalize()


async def _send_digest(to_email: str, events: list[dict]) -> None:
    # Most recent event first; use it for the "current" ticket fields (id/title/status/url)
    latest = events[-1]["data"]
    lines = [_event_summary_line(e["event"], e["data"]) for e in reversed(events)]
    digest_data = {
        "id": latest.get("id"),
        "title": latest.get("title"),
        "status": latest.get("status"),
        "ticket_url": latest.get("ticket_url"),
        "lines": lines,
    }
    try:
        template = jinja_env.get_template("ticket_digest.html")
        html_body = template.render(**digest_data)
    except Exception as exc:
        logger.warning("Email template error for digest: %s", exc)
        return

    try:
        message = MessageSchema(
            subject=f"[Ticket #{digest_data.get('id')}] {digest_data.get('title')} - {len(lines)} atualizações",
            recipients=[to_email],
            body=html_body,
            subtype=MessageType.html,
            headers={"Reply-To": settings.mail_from},
        )
        fm = FastMail(_get_conf())
        await fm.send_message(message)
        logger.info("Digest email sent to %s for ticket %s (%d event(s))", to_email, digest_data.get("id"), len(lines))
    except Exception as exc:
        logger.warning("Digest email failed to %s for ticket %s: %s", to_email, digest_data.get("id"), exc)
