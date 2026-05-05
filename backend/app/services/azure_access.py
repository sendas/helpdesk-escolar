from __future__ import annotations

import json
from pathlib import Path
import unicodedata

from app.config import settings
from app.models.user import UserRole

DEFAULT_SECRETARY_ONPREM_OUS = {"queiroz.local/aeeq/secretaria-eseq"}
DEFAULT_NON_TEACHING_ONPREM_OUS = {"queiroz.local/aeeq/_nao docentes"}
DEFAULT_EXCLUDED_ONPREM_OUS = {
    "queiroz.local/aeeq/_alunos",
    "queiroz.local/aeeq/alunos",
}
RUNTIME_SETTINGS_FILE = Path("/app/data/app_settings.json")


def is_email_admin(email: str) -> bool:
    if not email or not settings.azure_admin_emails:
        return False
    allowed = _csv(settings.azure_admin_emails)
    return email.lower() in allowed


def is_allowed_onprem_user(onprem_dn: str | None) -> bool:
    user_path = dn_to_path(onprem_dn)
    if not user_path:
        return False
    if is_student_onprem_user(onprem_dn):
        return False
    allowed_paths = runtime_allowed_onprem_ous()
    if not allowed_paths:
        return True
    return any(user_path == path or user_path.startswith(f"{path}/") for path in allowed_paths)


def is_student_onprem_user(onprem_dn: str | None) -> bool:
    user_path = dn_to_path(onprem_dn)
    return bool(user_path and _is_student_path(user_path))


def runtime_allowed_onprem_ous() -> set[str]:
    runtime_value = _runtime_setting("azure_allowed_onprem_ous")
    if isinstance(runtime_value, list):
        return {_normalize_path(str(item)) for item in runtime_value if str(item).strip()}
    if isinstance(runtime_value, str) and runtime_value.strip():
        return _csv(runtime_value)
    return _csv(settings.azure_allowed_onprem_ous)


def role_from_onprem_user(onprem_dn: str | None, fallback: UserRole = UserRole.TEACHER) -> UserRole:
    if _matches_any_path(onprem_dn, _csv(settings.azure_admin_onprem_ous)):
        return UserRole.ADMIN
    if _matches_any_path(onprem_dn, _csv(settings.azure_technician_onprem_ous)):
        return UserRole.TECHNICIAN
    if _matches_any_path(onprem_dn, _csv(settings.azure_secretary_onprem_ous) | DEFAULT_SECRETARY_ONPREM_OUS):
        return UserRole.SECRETARY
    if _matches_any_path(onprem_dn, _csv(settings.azure_non_teaching_onprem_ous) | DEFAULT_NON_TEACHING_ONPREM_OUS):
        return UserRole.NON_TEACHING
    return fallback


def _csv(value: str) -> set[str]:
    return {_normalize_path(item) for item in value.split(",") if item.strip()}


def _matches_any_path(onprem_dn: str | None, allowed_paths: set[str]) -> bool:
    if not onprem_dn or not allowed_paths:
        return False
    user_path = dn_to_path(onprem_dn)
    if not user_path:
        return False
    normalized_paths = {_normalize_path(path) for path in allowed_paths}
    return any(user_path == path or user_path.startswith(f"{path}/") for path in normalized_paths)


def _is_student_path(user_path: str) -> bool:
    path = _normalize_path(user_path)
    if any(path == excluded or path.startswith(f"{excluded}/") for excluded in DEFAULT_EXCLUDED_ONPREM_OUS):
        return True
    segments = {segment for segment in path.split("/") if segment}
    return bool({"aluno", "alunos", "_aluno", "_alunos"} & segments)


def dn_to_path(dn: str | None) -> str:
    if not dn:
        return ""
    dc_parts: list[str] = []
    ou_parts: list[str] = []

    for part in dn.split(","):
        key, _, value = part.strip().partition("=")
        key = key.upper()
        value = value.strip()
        if key == "DC" and value:
            dc_parts.append(value)
        elif key == "OU" and value:
            ou_parts.append(value)

    if not dc_parts:
        return ""
    domain = ".".join(dc_parts)
    ou_path = "/".join(reversed(ou_parts))
    return _normalize_path(f"{domain}/{ou_path}".strip("/"))


def _normalize_path(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _runtime_setting(key: str):
    try:
        if not RUNTIME_SETTINGS_FILE.exists():
            return None
        data = json.loads(RUNTIME_SETTINGS_FILE.read_text(encoding="utf-8"))
        return data.get(key) if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None
