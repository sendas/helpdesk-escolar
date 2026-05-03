import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from jinja2 import Environment, FileSystemLoader
from app.config import settings

_templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "email")

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


async def send_ticket_notification(to_email: str, event: str, ticket_data: dict) -> None:
    if not settings.mail_server:
        return

    try:
        template = jinja_env.get_template(f"ticket_{event}.html")
        html_body = template.render(**ticket_data)
    except Exception:
        return

    try:
        message = MessageSchema(
            subject=f"[Ticket #{ticket_data.get('id')}] {ticket_data.get('title')} - {event.replace('_', ' ').title()}",
            recipients=[to_email],
            body=html_body,
            subtype=MessageType.html,
        )
        fm = FastMail(_get_conf())
        await fm.send_message(message)
    except Exception:
        pass
