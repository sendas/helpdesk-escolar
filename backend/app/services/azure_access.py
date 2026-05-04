from __future__ import annotations

from app.config import settings
from app.models.user import UserRole


def is_email_admin(email: str) -> bool:
    if not email or not settings.azure_admin_emails:
        return False
    allowed = _csv(settings.azure_admin_emails)
    return email.lower() in allowed


def is_allowed_onprem_user(onprem_dn: str | None) -> bool:
    allowed_paths = _csv(settings.azure_allowed_onprem_ous)
    if not allowed_paths:
        return True
    return _matches_any_path(onprem_dn, allowed_paths)


def role_from_onprem_user(onprem_dn: str | None, fallback: UserRole = UserRole.TEACHER) -> UserRole:
    if _matches_any_path(onprem_dn, _csv(settings.azure_admin_onprem_ous)):
        return UserRole.ADMIN
    if _matches_any_path(onprem_dn, _csv(settings.azure_technician_onprem_ous)):
        return UserRole.TECHNICIAN
    return fallback


def _csv(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _matches_any_path(onprem_dn: str | None, allowed_paths: set[str]) -> bool:
    if not onprem_dn or not allowed_paths:
        return False
    user_path = _dn_to_path(onprem_dn)
    if not user_path:
        return False
    return any(user_path == path or user_path.startswith(f"{path}/") for path in allowed_paths)


def _dn_to_path(dn: str) -> str:
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
    return f"{domain}/{ou_path}".strip("/").lower()
