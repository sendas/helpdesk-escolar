import asyncio
import os
import logging
import uuid
from collections import defaultdict
from contextvars import ContextVar

import fastapi_mail.msg as _fastapi_mail_msg
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.config import settings

_templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
logger = logging.getLogger(__name__)

# autoescape: ticket titles, comments and form text are user input and must never become HTML in our emails
jinja_env = Environment(loader=FileSystemLoader(_templates_dir), autoescape=select_autoescape(["html"]))

# Notification digest: several updates to the same ticket, addressed to the same
# recipient, within a short window get merged into a single email instead of one
# per change (e.g. add comment + resolve + close in quick succession).
_DIGEST_WINDOW_SECONDS = settings.mail_digest_window_seconds
_pending: dict[tuple[str, int], list[dict]] = defaultdict(list)
_flush_tasks: dict[tuple[str, int], "asyncio.Task"] = {}


# fastapi-mail always makes up a Message-ID; emails to the support company need a known one, so that the later
# messages can say "this is a reply to that" (In-Reply-To/References) and land in the same ticket on their side
_forced_message_id: ContextVar[str | None] = ContextVar("forced_message_id", default=None)
_make_msgid = _fastapi_mail_msg.make_msgid
_fastapi_mail_msg.make_msgid = lambda *a, **k: _forced_message_id.get() or _make_msgid(*a, **k)


def new_thread_id(ticket_id: int) -> str:
    domain = (settings.mail_from or "helpdesk.local").rsplit("@", 1)[-1].strip(" >") or "helpdesk.local"
    return f"<helpdesk-{ticket_id}-{uuid.uuid4().hex[:12]}@{domain}>"


async def send_provider_email(to_email: str, event: str, ticket_data: dict, thread_id: str, first: bool) -> None:
    """One conversation per ticket with the support company: the first email opens it (Message-ID = thread_id),
    every later one is a reply to it, with the same subject — so their system adds to the same ticket instead of
    opening a new one each time."""
    if not settings.mail_server or _is_hidden_demo_action():
        return
    ticket_data = _normalize_ticket_data(ticket_data)
    try:
        html_body = jinja_env.get_template(f"ticket_{event}.html").render(**ticket_data)
    except Exception as exc:
        logger.warning("Email template error for event %s: %s", event, exc)
        return
    subject = f"[Ticket #{ticket_data.get('id')}] {ticket_data.get('title')}"
    headers = {"Reply-To": settings.mail_from}
    if not first:
        subject = "RE: " + subject
        headers.update({"In-Reply-To": thread_id, "References": thread_id})
    token = _forced_message_id.set(thread_id if first else None)
    try:
        message = MessageSchema(subject=subject, recipients=[to_email], body=html_body, subtype=MessageType.html, headers=headers)
        await FastMail(_get_conf()).send_message(message)
        logger.info("Email to the support company %s for ticket %s (%s)", to_email, ticket_data.get("id"), event)
    except Exception as exc:
        logger.warning("Email to the support company failed for ticket %s (%s): %s", ticket_data.get("id"), event, exc)
    finally:
        _forced_message_id.reset(token)


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


async def send_html(recipients: list[str], subject: str, html_body: str) -> None:
    """A ready-made HTML email (e.g. the monthly report). Raises on failure so the caller can report it."""
    if not settings.mail_server:
        raise RuntimeError("Envio de email não configurado no servidor.")
    message = MessageSchema(subject=subject, recipients=recipients, body=html_body, subtype=MessageType.html)
    await FastMail(_get_conf()).send_message(message)


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


async def send_no_access_contact(to_email: str, contact_data: dict) -> None:
    if not settings.mail_server:
        return
    try:
        template = jinja_env.get_template("no_access_contact.html")
        html_body = template.render(**contact_data)
    except Exception as exc:
        logger.warning("Email template error for no-access contact: %s", exc)
        return

    try:
        message = MessageSchema(
            subject=f"[Helpdesk] Sem acesso ao mail institucional — {contact_data.get('name', 'Desconhecido')}"
                    + (f" (aluno {contact_data.get('student_number')}, {contact_data.get('year')} {contact_data.get('class_name')})" if contact_data.get("is_student") else ""),
            recipients=[to_email],
            body=html_body,
            subtype=MessageType.html,
            headers={"Reply-To": contact_data.get("email") or settings.mail_from},
        )
        fm = FastMail(_get_conf())
        await fm.send_message(message)
        logger.info("No-access contact email sent to %s from %s", to_email, contact_data.get("name"))
    except Exception as exc:
        logger.warning("No-access contact email failed to %s: %s", to_email, exc)


async def send_private_message(to_email: str, data: dict) -> None:
    """Private message inside a ticket: sent only to its recipient, never merged into the update digest."""
    if not settings.mail_server or _is_hidden_demo_action() or to_email.lower().endswith("@demo.escola.pt"):
        return
    data = _normalize_ticket_data(data)
    try:
        html_body = jinja_env.get_template("ticket_private_message.html").render(**data)
        message = MessageSchema(
            subject=f"[Ticket #{data.get('id')}] [Privada] {data.get('title')}",
            recipients=[to_email],
            body=html_body,
            subtype=MessageType.html,
            headers={"Reply-To": settings.mail_from},
        )
        await FastMail(_get_conf()).send_message(message)
        logger.info("Private message email sent to %s for ticket %s", to_email, data.get("id"))
    except Exception as exc:
        logger.warning("Private message email failed to %s for ticket %s: %s", to_email, data.get("id"), exc)


async def send_reminder(to_email: str, data: dict) -> None:
    """Reminder set on an internal note. Sent right away (not merged into the update digest)."""
    if not settings.mail_server:
        return
    data = _normalize_ticket_data(data)
    created = data.get("note_created_at")
    if created:
        from datetime import timezone
        from zoneinfo import ZoneInfo
        data["note_created_at"] = created.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Lisbon")).strftime("%d/%m/%Y %H:%M")
    try:
        html_body = jinja_env.get_template("ticket_reminder.html").render(**data)
        message = MessageSchema(
            subject=f"[Lembrete] Ticket #{data.get('id')} — {data.get('title')}",
            recipients=[to_email],
            body=html_body,
            subtype=MessageType.html,
        )
        await FastMail(_get_conf()).send_message(message)
        logger.info("Reminder email sent to %s for ticket %s", to_email, data.get("id"))
    except Exception as exc:
        logger.warning("Reminder email failed to %s for ticket %s: %s", to_email, data.get("id"), exc)


def _normalize_ticket_data(ticket_data: dict) -> dict:
    ticket_data = dict(ticket_data)
    if ticket_data.get("id") and not ticket_data.get("ticket_url"):
        ticket_data["ticket_url"] = build_ticket_url(ticket_data["id"])
    if "status" in ticket_data:
        ticket_data["status"] = _STATUS_PT.get(str(ticket_data["status"]), str(ticket_data["status"]))
    if "priority" in ticket_data:
        ticket_data["priority"] = _PRIORITY_PT.get(str(ticket_data["priority"]), str(ticket_data["priority"]))
    return ticket_data


def _is_hidden_demo_action() -> bool:
    from app.api.deps import acting_as_demo
    if not acting_as_demo.get():
        return False
    from app.api.v1.settings import _read_settings
    return not _read_settings().get("demo_content_visible", False)


async def send_ticket_notification(to_email: str, event: str, ticket_data: dict) -> None:
    if not settings.mail_server or _is_hidden_demo_action():
        return
    if to_email.strip().lower().endswith("@demo.escola.pt"):
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


async def send_ticket_email_now(to_email: str, event: str, ticket_data: dict) -> None:
    """Right away, never merged into a digest (emails that carry their own full context, e.g. to the support company)."""
    if not settings.mail_server or _is_hidden_demo_action():
        return
    await _send_single(to_email, event, _normalize_ticket_data(ticket_data))


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
            subject=f"[Ticket #{ticket_data.get('id')}] {ticket_data.get('title')} — {_subject_label(event, ticket_data)}",
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


_SUBJECTS = {
    "created": "Pedido recebido",
    "commented": "Nova resposta",
    "updated": "Estado atualizado",
    "content_updated": "Pedido alterado",
    "assigned": "Atribuído a si",
    "escalated": "Pedido de suporte",
    "supplier_comment": "Nova mensagem",
    "supplier_updated": "Pedido concluído",
    "mentioned": "Foi mencionado",
    "status_request": "Ponto de situação pedido",
    "status_followup": "O seu pedido está a ser acompanhado",
}


def _subject_label(event: str, data: dict) -> str:
    if event == "updated" and data.get("status"):
        return f"Estado: {data['status']}"
    if event == "commented" and data.get("new_status"):
        return f"Nova resposta · {data['new_status']}"
    if event == "supplier_updated" and data.get("status"):
        return f"Estado: {data['status']}"
    return _SUBJECTS.get(event, "Atualização")


def _event_summary_line(event: str, data: dict) -> str:
    if event in ("commented", "supplier_comment"):
        author = data.get("author") or data.get("provider_name") or ""
        comment = (data.get("comment") or "").strip().replace("\n", " ")
        if len(comment) > 240:
            comment = comment[:240] + "…"
        line = f"Resposta de {author}: {comment}" if author else f"Resposta: {comment}"
        return line + (f" (estado: {data['new_status']})" if data.get("new_status") else "")
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
    if event == "status_followup":
        return "Pedido à espera da equipa: foi pedido o ponto de situação"
    if event == "status_request":
        return f"Sem resposta da equipa há {data.get('days')} dias — indique o ponto de situação"
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
