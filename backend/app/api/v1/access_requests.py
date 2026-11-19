"""Pedidos sem acesso: the "Não tenho acesso ao mail institucional" form, answered inside the helpdesk."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_perm
from app.models.access_request import AccessRequest, AccessRequestMessage
from app.models.user import User
from app.services import email_service
from app.services.names import short_name

router = APIRouter(prefix="/access-requests", tags=["access-requests"])
PERM = "access_requests.manage"
STATUSES = {"new", "answered", "closed"}
PROFILES = {"docente": "Docente", "nao_docente": "Não docente", "aluno": "Aluno"}
_LISBON = ZoneInfo("Europe/Lisbon")


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _person(u: User | None) -> dict | None:
    return {"id": u.id, "display_name": u.display_name} if u else None


def _summary(r: AccessRequest) -> dict:
    return {
        "id": r.id, "created_at": _iso(r.created_at), "updated_at": _iso(r.updated_at), "status": r.status,
        "profile": r.profile, "profile_label": PROFILES.get(r.profile, r.profile), "name": r.name, "email": r.email,
        "phone": r.phone, "student_number": r.student_number, "year": r.year, "class_name": r.class_name,
        "school": r.school, "recruitment_group": r.recruitment_group, "message": r.message,
        "handled_by": _person(r.handled_by), "messages_count": len(r.messages),
    }


def _detail(r: AccessRequest) -> dict:
    return {**_summary(r), "messages": [
        {"id": m.id, "created_at": _iso(m.created_at), "kind": m.kind, "body": m.body, "author": _person(m.author), "sent_ok": bool(m.sent_ok)}
        for m in r.messages
    ]}


async def _get(db: AsyncSession, request_id: int) -> AccessRequest:
    r = await db.get(AccessRequest, request_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado.")
    return r


@router.get("")
async def list_requests(state: str = Query("open"), q: str = Query(""), db: AsyncSession = Depends(get_db),
                        _: User = Depends(require_perm(PERM))):
    """state: open (new + answered), new, answered, closed or all."""
    query = select(AccessRequest).order_by(AccessRequest.updated_at.desc()).limit(300)
    if state == "open":
        query = query.where(AccessRequest.status.in_(["new", "answered"]))
    elif state in STATUSES:
        query = query.where(AccessRequest.status == state)
    rows = list((await db.execute(query)).scalars())
    term = q.strip().lower()
    if term:
        rows = [r for r in rows if term in " ".join([r.name, r.email, r.student_number, r.phone, r.school, r.message]).lower()]
    counts = dict((await db.execute(select(AccessRequest.status, func.count()).group_by(AccessRequest.status))).all())
    return {"items": [_summary(r) for r in rows], "counts": {s: counts.get(s, 0) for s in STATUSES}}


@router.get("/count")
async def waiting_count(db: AsyncSession = Depends(get_db), _: User = Depends(require_perm(PERM))):
    """Menu badge: requests waiting for the team."""
    n = (await db.execute(select(func.count()).select_from(AccessRequest).where(AccessRequest.status == "new"))).scalar_one()
    return {"new": n}


@router.get("/{request_id}")
async def get_request(request_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm(PERM))):
    return _detail(await _get(db, request_id))


class ReplyIn(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)
    # email: sent to the person · phone: a call, only recorded · note: internal note, only the team sees it
    kind: str = "email"
    close: bool = False


@router.post("/{request_id}/reply")
async def reply(request_id: int, data: ReplyIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_perm(PERM))):
    from app.api.v1.settings import _read_settings
    r = await _get(db, request_id)
    kind = data.kind if data.kind in {"email", "phone", "note"} else "email"
    body = data.body.strip()
    if kind == "email" and not r.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta pessoa não indicou email: registe o contacto por telefone ou uma nota.")
    sent = True
    if kind == "email":
        original_when = r.created_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(_LISBON).strftime("%d/%m/%Y %H:%M")
        sent = await email_service.send_access_reply(r.email, {
            "id": r.id, "body": body, "first_name": (r.name.split() or [""])[0], "author": short_name(user.display_name),
            "org_name": _read_settings().get("org_name") or "Agrupamento de Escolas", "original": r.message, "created": original_when,
        })
        if not sent:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível enviar o email. Verifique o envio de email nas Configurações.")
    r.messages.append(AccessRequestMessage(author_id=user.id, kind=kind, body=body, sent_ok=1 if sent else 0))
    if kind != "note":
        r.status = "answered"
    if data.close:
        r.status = "closed"
    r.handled_by_id = user.id
    r.updated_at = datetime.utcnow()
    await db.commit()
    return _detail(await _get(db, request_id))


class StatusIn(BaseModel):
    status: str


@router.patch("/{request_id}")
async def set_status(request_id: int, data: StatusIn, db: AsyncSession = Depends(get_db), user: User = Depends(require_perm(PERM))):
    if data.status not in STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado inválido.")
    r = await _get(db, request_id)
    r.status = data.status
    r.handled_by_id = user.id
    r.updated_at = datetime.utcnow()
    await db.commit()
    return _detail(await _get(db, request_id))


async def add_inbound_reply(db: AsyncSession, request_id: int, sender: str, body: str, message_id: str) -> bool:
    """A reply by email from the person (email_ingest): added to the request, which goes back to "waiting for the team".
    Only from the address the person gave; each email once."""
    r = await db.get(AccessRequest, request_id)
    if not r or not r.email or r.email.strip().lower() != (sender or "").strip().lower() or not body.strip():
        return False
    if (await db.execute(select(AccessRequestMessage.id).where(AccessRequestMessage.message_id == message_id))).first():
        return False
    r.messages.append(AccessRequestMessage(kind="inbound", body=body.strip(), message_id=message_id))
    r.status = "new"
    r.updated_at = datetime.utcnow()
    return True


# ── Importing the requests that arrived before this section existed ────────────────────────────────────────────
# They only exist as the alert emails ("[Helpdesk] Sem acesso ao mail institucional — …", template
# no_access_contact.html): read back from the mailbox they were sent to, through Microsoft Graph.
import html as _html
import re as _re

_ALERT_SUBJECT = "Sem acesso ao mail institucional"
_LABELS = {"Perfil": "profile", "Nome": "name", "N.º do cartão": "student_number", "Ano / turma": "year_class",
           "Email": "email", "Telefone": "phone", "Grupo de recrutamento": "recruitment_group", "Escola": "school"}
_PROFILE_KEYS = {"aluno": "aluno", "docente": "docente", "não docente": "nao_docente", "nao docente": "nao_docente"}


def _text(fragment: str) -> str:
    t = _re.sub(r"(?is)<br\s*/?>", "\n", fragment)
    t = _re.sub(r"(?s)<[^>]+>", "", t)
    return _html.unescape(t).replace("\xa0", " ").strip()


def parse_alert_email(body_html: str) -> dict | None:
    """The fields of an alert email, or None if it is not one."""
    fields: dict[str, str] = {}
    for label, value in _re.findall(r"(?is)<td[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,40}?)\s*(?:</[^>]+>\s*)*</td>\s*<td[^>]*>(.*?)</td>", body_html):
        key = _LABELS.get(_text(label))
        if key:
            fields[key] = _text(value)
    m = _re.search(r"(?is)Mensagem\s*</div>\s*<div[^>]*>(.*?)</div>", body_html)
    if not fields.get("name") or not m:
        return None
    email = fields.get("email", "")
    email = "" if not _re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) else email.lower()
    phone = "" if fields.get("phone", "—").strip() in ("—", "-") else fields["phone"]
    year, class_name = "", ""
    if fields.get("year_class"):
        parts = fields["year_class"].split()
        year, class_name = (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else (parts[0], "")
    clean = lambda v: "" if (v or "").strip() in ("—", "-") else (v or "").strip()  # noqa: E731
    return {
        "profile": _PROFILE_KEYS.get(fields.get("profile", "").lower(), "docente"), "name": fields["name"], "email": email,
        "phone": phone, "student_number": clean(fields.get("student_number")).lower(), "year": year, "class_name": class_name.upper(),
        "school": clean(fields.get("school")), "recruitment_group": clean(fields.get("recruitment_group")), "message": _text(m.group(1)),
    }


class ImportIn(BaseModel):
    days: int = Field(90, ge=1, le=365)


@router.post("/import-previous")
async def import_previous(data: ImportIn, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm(PERM))):
    import asyncio
    import httpx
    from app.api.v1.settings import _read_settings
    from app.config import settings as cfg
    from app.services.email_ingest import _get_graph_token
    if (cfg.mail_reply_provider or "").strip().lower() != "graph" or not cfg.azure_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Só é possível importar com a leitura de emails pelo Microsoft Graph.")
    mailboxes = list(dict.fromkeys(m.strip().lower() for m in [
        _read_settings().get("no_access_contact_email") or "", cfg.graph_mail_user or "", cfg.mail_from or ""] if m and "@" in m))
    token = await asyncio.to_thread(_get_graph_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Não foi possível ligar ao Microsoft 365.")
    since = datetime.utcnow() - timedelta(days=data.days)
    known = set((await db.execute(select(AccessRequest.source_message_id).where(AccessRequest.source_message_id.is_not(None)))).scalars())
    added, read_ok, errors = 0, 0, []
    async with httpx.AsyncClient(timeout=30) as client:
        for box in mailboxes:
            url = f"https://graph.microsoft.com/v1.0/users/{box}/messages"
            params = {"$search": f'"subject:{_ALERT_SUBJECT}"', "$top": "100", "$select": "subject,body,receivedDateTime,internetMessageId"}
            try:
                resp = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}", "Prefer": 'outlook.body-content-type="html"'})
            except Exception:
                errors.append(box)
                continue
            if resp.status_code != 200:
                errors.append(box)
                continue
            read_ok += 1
            for raw in resp.json().get("value") or []:
                mid = (raw.get("internetMessageId") or "").strip()
                received = datetime.fromisoformat((raw.get("receivedDateTime") or "").replace("Z", "+00:00")).replace(tzinfo=None) if raw.get("receivedDateTime") else None
                if not mid or mid in known or (received and received < since) or _ALERT_SUBJECT not in (raw.get("subject") or ""):
                    continue
                fields = parse_alert_email(((raw.get("body") or {}).get("content")) or "")
                if not fields:
                    continue
                db.add(AccessRequest(**fields, source_message_id=mid, created_at=received or datetime.utcnow(), updated_at=received or datetime.utcnow()))
                known.add(mid)
                added += 1
    if not read_ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Não foi possível ler a caixa de email ({', '.join(errors) or 'sem caixa configurada'}).")
    await db.commit()
    return {"added": added, "mailboxes": mailboxes}
