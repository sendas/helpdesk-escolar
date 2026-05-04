import json
import os
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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
}


@router.get("/public")
async def public_settings():
    return _read_settings()


@router.put("")
async def update_settings(
    org_name: str = Form(...),
    logo: UploadFile | None = File(None),
    _: User = Depends(require_admin),
):
    data = _read_settings()
    data["org_name"] = org_name.strip() or DEFAULT_SETTINGS["org_name"]

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

    _write_settings(data)
    return data


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
