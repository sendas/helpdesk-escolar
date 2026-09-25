"""Microsoft Teams channel notifications through a Teams "Workflows" webhook (Power Automate).

The helpdesk only sends: nothing needs to reach the server from the internet. Messages are Adaptive Cards, which is
the format the "Post to a channel when a webhook request is received" workflow expects.
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx

logger = logging.getLogger(__name__)
_LISBON = ZoneInfo("Europe/Lisbon")

EVENTS = {
    "ticket_created": "Novo ticket",
    "support_waiting": "Pedido de apoio ao vivo à espera",
    "ticket_overdue": "Ticket fora do prazo",
    "requester_reply": "Nova resposta de quem fez o pedido",
}
PRIORITY_PT = {"low": "Baixa", "medium": "Média", "high": "Alta", "urgent": "Urgente"}


def _settings() -> dict:
    from app.api.v1.settings import _read_settings
    return _read_settings()


def enabled(event: str) -> bool:
    s = _settings()
    return bool(s.get("teams_webhook_url")) and event in (s.get("teams_events") or [])


def _short(name: str | None) -> str:
    from app.services.chat_service import short_name
    return short_name(name)


def build_card(title: str, text: str = "", facts: list[tuple[str, str]] | None = None, url: str | None = None,
               button: str = "Abrir no helpdesk", accent: str = "accent") -> dict:
    body: list[dict] = [
        {"type": "TextBlock", "text": title, "weight": "Bolder", "size": "Medium", "wrap": True, "color": accent},
    ]
    if text:
        body.append({"type": "TextBlock", "text": text, "wrap": True, "spacing": "Small"})
    if facts:
        body.append({"type": "FactSet", "facts": [{"title": k, "value": v} for k, v in facts if v]})
    card = {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "type": "AdaptiveCard", "version": "1.4", "body": body}
    if url:
        card["actions"] = [{"type": "Action.OpenUrl", "title": button, "url": url}]
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None, "content": card}]}


async def post(payload: dict, webhook_url: str | None = None) -> tuple[bool, str]:
    url = webhook_url or _settings().get("teams_webhook_url")
    if not url:
        return False, "Endereço do Teams não configurado."
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code >= 300:
            logger.warning("Teams webhook answered %s: %s", resp.status_code, resp.text[:300])
            return False, f"O Teams respondeu com o código {resp.status_code}."
        return True, ""
    except Exception as exc:
        logger.warning("Teams webhook failed: %s", exc)
        return False, "Não foi possível contactar o Teams."


def _fire(event: str, payload: dict) -> None:
    from app.services.email_service import _is_hidden_demo_action
    if not enabled(event) or _is_hidden_demo_action():
        return
    asyncio.create_task(post(payload))


def _ticket_url(ticket_id: int) -> str:
    from app.services.email_service import build_ticket_url
    return build_ticket_url(ticket_id)


def _ticket_facts(ticket) -> list[tuple[str, str]]:
    assignees = ", ".join(_short(a.display_name) for a in (ticket.assignees or [])) or (ticket.group.name if ticket.group else "")
    return [
        ("Solicitante", _short(ticket.creator.display_name) if ticket.creator else ""),
        ("Escola", ticket.school.name if ticket.school else ""),
        ("Categoria", ticket.category.name if ticket.category else ""),
        ("Prioridade", PRIORITY_PT.get(ticket.priority.value, ticket.priority.value) if ticket.priority else ""),
        ("Responsável", assignees or "Por atribuir"),
    ]


def ticket_created(ticket) -> None:
    if ticket.creator and ticket.creator.auth_provider == "demo":
        return
    text = (ticket.description or "").strip()
    _fire("ticket_created", build_card(
        f"🎫 Novo ticket T-{ticket.id}: {ticket.title}", text[:400] + ("…" if len(text) > 400 else ""),
        _ticket_facts(ticket), _ticket_url(ticket.id), "Abrir ticket",
    ))


def requester_reply(ticket, body: str) -> None:
    _fire("requester_reply", build_card(
        f"💬 {_short(ticket.creator.display_name)} respondeu no T-{ticket.id}: {ticket.title}",
        body[:400] + ("…" if len(body) > 400 else ""), _ticket_facts(ticket), _ticket_url(ticket.id), "Abrir ticket",
    ))


def support_waiting(conv_id: int, requester_name: str, body: str, school: str = "") -> None:
    from app.config import settings
    url = f"{settings.frontend_url.rstrip('/')}/chat?tab=apoio&c={conv_id}"
    _fire("support_waiting", build_card(
        f"🟠 Apoio ao vivo: {_short(requester_name)} está à espera", body[:400],
        [("Escola", school), ("Pedido às", datetime.now(_LISBON).strftime("%H:%M"))], url, "Atender",
        accent="warning",
    ))


async def notify_overdue(db) -> None:
    """Announce, once, every ticket that has just gone past its response time."""
    if not enabled("ticket_overdue"):
        return
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.api.v1.settings import _read_settings, _write_settings
    from app.models.ticket import Ticket, TicketStatus
    from app.services.ticket_service import is_overdue
    rows = (
        await db.execute(
            select(Ticket).where(Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]), Ticket.archived_at.is_(None))
            .options(selectinload(Ticket.category), selectinload(Ticket.creator), selectinload(Ticket.school),
                     selectinload(Ticket.assignees), selectinload(Ticket.group))
        )
    ).scalars().all()
    data = _read_settings()
    done = set(data.get("teams_overdue_notified") or [])
    first_run = "teams_overdue_notified" not in data
    new = [t for t in rows if is_overdue(t) and t.id not in done and not (t.creator and t.creator.auth_provider == "demo")]
    if not first_run:  # the first run only records what is already late, so the channel is not flooded
        for t in new[:20]:
            await post(build_card(f"⏰ T-{t.id} passou o tempo de resposta: {t.title}", "", _ticket_facts(t), _ticket_url(t.id), "Abrir ticket", accent="attention"))
    open_ids = {t.id for t in rows}
    data["teams_overdue_notified"] = sorted((done & open_ids) | {t.id for t in new})
    _write_settings(data)
