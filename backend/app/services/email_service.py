import os
import logging
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jinja2 import Environment, FileSystemLoader
from app.config import settings

_templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
logger = logging.getLogger(__name__)

jinja_env = Environment(loader=FileSystemLoader(_templates_dir))


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


async def send_ticket_notification(to_email: str, event: str, ticket_data: dict) -> None:
    if not settings.mail_server:
        return
    ticket_data = dict(ticket_data)
    if ticket_data.get("id") and not ticket_data.get("ticket_url"):
        ticket_data["ticket_url"] = build_ticket_url(ticket_data["id"])
    if "status" in ticket_data:
        ticket_data["status"] = _STATUS_PT.get(str(ticket_data["status"]), str(ticket_data["status"]))
    if "priority" in ticket_data:
        ticket_data["priority"] = _PRIORITY_PT.get(str(ticket_data["priority"]), str(ticket_data["priority"]))

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
