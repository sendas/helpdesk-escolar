from __future__ import annotations

import msal
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserRole
from app.services import azure_access


GRAPH_USERS_URL = "https://graph.microsoft.com/v1.0/users"


class AzureImportError(Exception):
    pass


async def import_azure_users(db: AsyncSession) -> dict:
    if not settings.azure_ad_enabled:
        raise AzureImportError("Microsoft Entra ID não está ativo.")
    if not all([settings.azure_tenant_id, settings.azure_client_id, settings.azure_client_secret]):
        raise AzureImportError("Configuração Microsoft Entra ID incompleta.")

    token = _get_graph_token()
    users = await _fetch_graph_users(token)

    existing = (await db.execute(select(User))).scalars().all()
    by_email = {u.email.lower(): u for u in existing if u.email}
    by_username = {u.username.lower(): u for u in existing if u.username}
    usernames = {u.username.lower() for u in existing if u.username}

    created = 0
    updated = 0
    skipped = 0
    skipped_guests = 0
    skipped_disabled = 0
    skipped_outside_ou = 0
    skipped_students = 0
    skipped_without_email = 0
    role_changes = 0
    manual_locked = 0

    for item in users:
        if item.get("userType") == "Guest":
            skipped_guests += 1
            skipped += 1
            continue
        if item.get("accountEnabled") is False:
            skipped_disabled += 1
            skipped += 1
            continue

        onprem_dn = item.get("onPremisesDistinguishedName")
        if azure_access.is_student_onprem_user(onprem_dn):
            skipped_students += 1
            skipped += 1
            continue
        if not azure_access.is_allowed_onprem_user(onprem_dn):
            skipped_outside_ou += 1
            skipped += 1
            continue

        email = _preferred_email(item)
        if not email:
            skipped_without_email += 1
            skipped += 1
            continue

        email = email.strip()
        user_principal_name = (item.get("userPrincipalName") or "").strip()
        display_name = item.get("displayName") or email
        imported_role = azure_access.role_from_onprem_user(onprem_dn)
        onprem_path = azure_access.dn_to_path(onprem_dn) or None
        department = item.get("department") or onprem_path or None
        user = by_email.get(email.lower())
        if not user and user_principal_name:
            user = by_email.get(user_principal_name.lower())
        if not user and user_principal_name:
            user = by_username.get(user_principal_name.split("@", 1)[0].lower())

        if user:
            changed = False
            if user.email.lower() != email.lower() and _email_available(by_email, email, user):
                by_email.pop(user.email.lower(), None)
                user.email = email
                by_email[email.lower()] = user
                changed = True
            if user.display_name != display_name:
                user.display_name = display_name
                changed = True
            if department and user.department != department:
                user.department = department
                changed = True
            if user.onprem_dn != onprem_dn:
                user.onprem_dn = onprem_dn
                changed = True
            if user.onprem_path != onprem_path:
                user.onprem_path = onprem_path
                changed = True
            if user.role_locked:
                manual_locked += 1
            elif user.role != imported_role:
                user.role = imported_role
                user.role_source = "entra"
                role_changes += 1
                changed = True
            if changed:
                updated += 1
            continue

        username = _unique_username(user_principal_name or email, usernames)
        user = User(
            username=username,
            email=email,
            display_name=display_name,
            department=department,
            role=imported_role,
            role_source="entra",
            role_locked=False,
            onprem_dn=onprem_dn,
            onprem_path=onprem_path,
            auth_provider="azure",
            is_active=True,
        )
        db.add(user)
        by_email[email.lower()] = user
        created += 1

    await db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total": len(users),
        "role_changes": role_changes,
        "manual_locked": manual_locked,
        "skipped_guests": skipped_guests,
        "skipped_disabled": skipped_disabled,
        "skipped_outside_ou": skipped_outside_ou,
        "skipped_students": skipped_students,
        "skipped_without_email": skipped_without_email,
    }


def _get_graph_token() -> str:
    app = msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        detail = result.get("error_description") or result.get("error") or "Erro ao obter token Graph."
        raise AzureImportError(detail)
    return result["access_token"]


async def _fetch_graph_users(access_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "$select": "id,displayName,mail,userPrincipalName,proxyAddresses,otherMails,department,accountEnabled,userType,onPremisesDistinguishedName",
        "$top": "999",
    }
    users: list[dict] = []
    next_url: str | None = GRAPH_USERS_URL

    async with httpx.AsyncClient(timeout=30) as client:
        while next_url:
            resp = await client.get(next_url, headers=headers, params=params if next_url == GRAPH_USERS_URL else None)
            if resp.status_code != 200:
                raise AzureImportError(resp.text)
            payload = resp.json()
            users.extend(payload.get("value", []))
            next_url = payload.get("@odata.nextLink")
            params = None
    return users


def _unique_username(upn_or_email: str, usernames: set[str]) -> str:
    base = (upn_or_email.split("@")[0] or "user").strip().lower()
    candidate = base
    counter = 2
    while candidate.lower() in usernames:
        candidate = f"{base}{counter}"
        counter += 1
    usernames.add(candidate.lower())
    return candidate


def _preferred_email(item: dict) -> str:
    candidates: list[str] = []
    for value in [item.get("mail")]:
        if value:
            candidates.append(value)
    proxy_addresses = item.get("proxyAddresses") or []
    primary_proxy = [addr[5:] for addr in proxy_addresses if isinstance(addr, str) and addr.startswith("SMTP:")]
    secondary_proxy = [addr[5:] for addr in proxy_addresses if isinstance(addr, str) and addr.startswith("smtp:")]
    candidates.extend(primary_proxy)
    candidates.extend(secondary_proxy)
    candidates.extend(item.get("otherMails") or [])
    if item.get("userPrincipalName"):
        candidates.append(item["userPrincipalName"])

    normalized = []
    seen = set()
    for candidate in candidates:
        email = str(candidate).strip().lower()
        if "@" not in email or email in seen:
            continue
        seen.add(email)
        normalized.append(email)
    if not normalized:
        return ""
    for email in normalized:
        if email.endswith("@queiroz.pt"):
            return email
    for email in normalized:
        if ".onmicrosoft.com" not in email:
            return email
    return normalized[0]


def _email_available(by_email: dict[str, User], email: str, user: User) -> bool:
    existing = by_email.get(email.lower())
    return existing is None or existing.id == user.id
