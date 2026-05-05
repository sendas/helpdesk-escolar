import json
import os
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from app.api.deps import require_admin
from app.models.user import User

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
    "support_provider_name": "Fornecedor externo",
    "support_provider_email": "",
    "azure_allowed_onprem_ous": [],
}


class AzureSyncSettings(BaseModel):
    allowed_onprem_ous: list[str] = []


@router.get("/public")
async def public_settings():
    return _read_settings()


@router.put("")
async def update_settings(
    org_name: str = Form(...),
    support_provider_name: str = Form("Fornecedor externo"),
    support_provider_email: str = Form(""),
    logo: UploadFile | None = File(None),
    _: User = Depends(require_admin),
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
async def get_azure_sync_settings(_: User = Depends(require_admin)):
    allowed = _normalize_ou_list(_read_settings().get("azure_allowed_onprem_ous", []))
    return {"allowed_onprem_ous": allowed}


@router.put("/azure-sync")
async def update_azure_sync_settings(payload: AzureSyncSettings, _: User = Depends(require_admin)):
    data = _read_settings()
    data["azure_allowed_onprem_ous"] = _normalize_ou_list(payload.allowed_onprem_ous)
    _write_settings(data)
    return {"allowed_onprem_ous": data["azure_allowed_onprem_ous"]}


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
