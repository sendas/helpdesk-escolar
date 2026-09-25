import json
import os
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from app.api.deps import require_admin, require_perm
from app.models.user import User
from app.config import settings as app_config

router = APIRouter(prefix="/settings", tags=["settings"])

DATA_DIR = "/app/data"
SETTINGS_FILE = os.path.join(DATA_DIR, "app_settings.json")
LOGO_DIR = os.path.join(DATA_DIR, "uploads", "branding")
MAX_LOGO_BYTES = 2 * 1024 * 1024
ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}

DEFAULT_SETTINGS = {
    "org_name": "Agrupamento de Escolas Eça de Queirós",
    "logo_url": "",
    "favicon_url": "",
    "support_provider_name": "Empresa de apoio informático",
    "support_provider_email": "",
    "azure_allowed_onprem_ous": [],
    "knowledge_enabled": True,
    "suggestion_emails": [],
    "category_warnings_enabled": True,
    "login_notice_enabled": False,
    "login_notice_text": (
        "Esta plataforma é para uso exclusivo de docentes e não docentes do "
        "Agrupamento de Escolas Eça de Queirós. Caso não consiga fazer login ou "
        "não tenha acesso ao seu mail institucional, envie um mail (usando o seu "
        "mail pessoal) para helpdesk_aeeq@queiroz.pt. Obrigado."
    ),
    "no_access_contact_email": "helpdesk_aeeq@queiroz.pt",
    "ui_design": "modern",
    "demo_mode_enabled": False,
    "demo_profiles": ["teacher"],
    "demo_content_visible": False,
    # Live support chat (balão de apoio); days are ISO weekdays (1 = segunda-feira)
    "support_chat_enabled": True,
    "support_wait_minutes": 5,
    "support_hours": {
        "1": {"enabled": True, "start": "14:00", "end": "17:00"},
        "2": {"enabled": True, "start": "10:00", "end": "13:00"},
        "3": {"enabled": True, "start": "14:00", "end": "17:00"},
        "4": {"enabled": True, "start": "10:00", "end": "13:00"},
        "5": {"enabled": True, "start": "10:00", "end": "13:00"},
        "6": {"enabled": False, "start": "10:00", "end": "13:00"},
        "7": {"enabled": False, "start": "10:00", "end": "13:00"},
    },
    # Microsoft Teams channel notifications (Workflows webhook)
    "teams_webhook_url": "",
    "teams_events": ["ticket_created", "support_waiting", "ticket_overdue", "requester_reply"],
}

# Never sent by /settings/public (the Teams address lets anyone post in the channel)
PRIVATE_KEYS = {"teams_webhook_url", "teams_overdue_notified", "role_permissions_granted"}

UI_DESIGNS = {"modern", "classic"}
DEMO_PROFILES = ("teacher", "technician", "admin")


class AzureSyncSettings(BaseModel):
    allowed_onprem_ous: list[str] = []


class FeatureSettings(BaseModel):
    knowledge_enabled: bool = True
    category_warnings_enabled: bool = True


class LoginNoticeSettings(BaseModel):
    enabled: bool = False
    text: str = ""


class NoAccessContactSettings(BaseModel):
    email: str = ""


class DesignSettings(BaseModel):
    design: str = "modern"


class DemoModeSettings(BaseModel):
    enabled: bool = False
    profiles: list[str] = ["teacher"]
    content_visible: bool | None = None


class SuggestionEmailSettings(BaseModel):
    emails: list[str] = []


@router.get("/public")
async def public_settings():
    return {k: v for k, v in _read_settings().items() if k not in PRIVATE_KEYS}


@router.put("")
async def update_settings(
    org_name: str = Form(...),
    support_provider_name: str = Form("Empresa de apoio informático"),
    support_provider_email: str = Form(""),
    logo: UploadFile | None = File(None),
    _: User = Depends(require_perm("settings.manage")),
):
    data = _read_settings()
    data["org_name"] = org_name.strip() or DEFAULT_SETTINGS["org_name"]
    data["support_provider_name"] = support_provider_name.strip() or DEFAULT_SETTINGS["support_provider_name"]
    data["support_provider_email"] = support_provider_email.strip()

    if logo and logo.filename:
        if logo.content_type not in ALLOWED_LOGO_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logotipo inválido. Use PNG, JPG, SVG ou WEBP.")
        content = await logo.read()
        if len(content) > MAX_LOGO_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logotipo demasiado grande. Máximo: 2 MB.")
        os.makedirs(LOGO_DIR, exist_ok=True)
        ext = os.path.splitext(logo.filename)[1].lower()
        stored_name = f"logo-{uuid.uuid4().hex}{ext}"
        with open(os.path.join(LOGO_DIR, stored_name), "wb") as f:
            f.write(content)
        data["logo_url"] = f"/uploads/branding/{stored_name}"
        data["favicon_url"] = data["logo_url"]

    _write_settings(data)
    return data


@router.get("/azure-sync")
async def get_azure_sync_settings(_: User = Depends(require_perm("settings.manage"))):
    allowed = _normalize_ou_list(_read_settings().get("azure_allowed_onprem_ous", []))
    return {"allowed_onprem_ous": allowed}


@router.put("/azure-sync")
async def update_azure_sync_settings(payload: AzureSyncSettings, _: User = Depends(require_perm("settings.manage"))):
    data = _read_settings()
    data["azure_allowed_onprem_ous"] = _normalize_ou_list(payload.allowed_onprem_ous)
    _write_settings(data)
    return {"allowed_onprem_ous": data["azure_allowed_onprem_ous"]}


@router.put("/features")
async def update_feature_settings(payload: FeatureSettings, _: User = Depends(require_perm("settings.manage"))):
    data = _read_settings()
    data["knowledge_enabled"] = payload.knowledge_enabled
    data["category_warnings_enabled"] = payload.category_warnings_enabled
    _write_settings(data)
    return {"knowledge_enabled": data["knowledge_enabled"], "category_warnings_enabled": data["category_warnings_enabled"]}


@router.put("/login-notice")
async def update_login_notice(payload: LoginNoticeSettings, _: User = Depends(require_perm("settings.manage"))):
    data = _read_settings()
    data["login_notice_enabled"] = payload.enabled
    text = payload.text.strip()
    if text:
        data["login_notice_text"] = text
    _write_settings(data)
    return {"login_notice_enabled": data["login_notice_enabled"], "login_notice_text": data["login_notice_text"]}


@router.put("/no-access-contact")
async def update_no_access_contact(payload: NoAccessContactSettings, _: User = Depends(require_perm("settings.manage"))):
    data = _read_settings()
    email = payload.email.strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email inválido")
    data["no_access_contact_email"] = email
    _write_settings(data)
    return {"no_access_contact_email": data["no_access_contact_email"]}


@router.put("/design")
async def update_design(payload: DesignSettings, _: User = Depends(require_perm("settings.manage"))):
    if payload.design not in UI_DESIGNS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Design inválido")
    data = _read_settings()
    data["ui_design"] = payload.design
    _write_settings(data)
    return {"ui_design": data["ui_design"]}


@router.put("/demo-mode")
async def update_demo_mode(payload: DemoModeSettings, _: User = Depends(require_perm("settings.manage"))):
    profiles = [p for p in DEMO_PROFILES if p in payload.profiles]
    if payload.enabled and not profiles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escolha pelo menos um perfil para o modo demo")
    data = _read_settings()
    data["demo_mode_enabled"] = payload.enabled
    data["demo_profiles"] = profiles or ["teacher"]
    if payload.content_visible is not None:
        data["demo_content_visible"] = payload.content_visible
    _write_settings(data)
    return {
        "demo_mode_enabled": data["demo_mode_enabled"],
        "demo_profiles": data["demo_profiles"],
        "demo_content_visible": data.get("demo_content_visible", False),
    }


class SupportDay(BaseModel):
    enabled: bool = False
    start: str = "09:00"
    end: str = "17:00"


class SupportChatSettings(BaseModel):
    enabled: bool = True
    wait_minutes: int = 5
    hours: dict[str, SupportDay] = {}


@router.put("/support-chat")
async def update_support_chat(payload: SupportChatSettings, _: User = Depends(require_perm("settings.manage"))):
    import re
    hours = {}
    for day in [str(d) for d in range(1, 8)]:
        d = payload.hours.get(day) or SupportDay()
        if not (re.fullmatch(r"\d{2}:\d{2}", d.start) and re.fullmatch(r"\d{2}:\d{2}", d.end)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Horas inválidas: use o formato HH:MM.")
        if d.enabled and d.start >= d.end:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A hora de fim tem de ser depois da hora de início.")
        hours[day] = d.model_dump()
    data = _read_settings()
    data["support_chat_enabled"] = payload.enabled
    data["support_wait_minutes"] = max(1, min(payload.wait_minutes, 120))
    data["support_hours"] = hours
    _write_settings(data)
    return {k: data[k] for k in ("support_chat_enabled", "support_wait_minutes", "support_hours")}


class TeamsSettings(BaseModel):
    webhook_url: str = ""
    events: list[str] = []


def _teams_view(data: dict) -> dict:
    url = data.get("teams_webhook_url") or ""
    return {"configured": bool(url), "webhook_url": url, "events": data.get("teams_events") or []}


@router.get("/teams")
async def get_teams(_: User = Depends(require_perm("settings.manage"))):
    return _teams_view(_read_settings())


@router.put("/teams")
async def update_teams(payload: TeamsSettings, _: User = Depends(require_perm("settings.manage"))):
    from app.services.teams_service import EVENTS
    url = payload.webhook_url.strip()
    if url and not url.startswith("https://"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O endereço do Teams tem de começar por https://")
    data = _read_settings()
    data["teams_webhook_url"] = url
    data["teams_events"] = [e for e in payload.events if e in EVENTS]
    _write_settings(data)
    return _teams_view(data)


@router.post("/teams/test")
async def test_teams(payload: TeamsSettings, current_user: User = Depends(require_perm("settings.manage"))):
    from app.services import teams_service
    url = payload.webhook_url.strip() or _read_settings().get("teams_webhook_url")
    card = teams_service.build_card(
        "✅ Helpdesk ligado a este canal",
        f"Mensagem de teste enviada por {teams_service._short(current_user.display_name)}. Os avisos do helpdesk vão aparecer aqui.",
        url=app_config.frontend_url, button="Abrir o helpdesk",
    )
    ok, error = await teams_service.post(card, url)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return {"ok": True}


@router.put("/suggestion-emails")
async def update_suggestion_emails(payload: SuggestionEmailSettings, _: User = Depends(require_perm("settings.manage"))):
    data = _read_settings()
    clean = [e.strip().lower() for e in payload.emails if e.strip()]
    data["suggestion_emails"] = clean
    _write_settings(data)
    return {"suggestion_emails": data["suggestion_emails"]}


def _read_settings() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)


def _write_settings(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize_ou_list(value) -> list[str]:
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, list):
        items = value
    else:
        items = []
    seen: set[str] = set()
    normalized: list[str] = []
    for item in items:
        ou = str(item).strip()
        key = ou.lower()
        if ou and key not in seen:
            normalized.append(ou)
            seen.add(key)
    return normalized
