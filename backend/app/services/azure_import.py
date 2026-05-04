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
    usernames = {u.username.lower() for u in existing if u.username}

    created = 0
    updated = 0
    skipped = 0

    for item in users:
        if item.get("userType") == "Guest" or item.get("accountEnabled") is False:
            skipped += 1
            continue

        onprem_dn = item.get("onPremisesDistinguishedName")
        if not azure_access.is_allowed_onprem_user(onprem_dn):
            skipped += 1
            continue

        email = item.get("mail") or item.get("userPrincipalName")
        if not email:
            skipped += 1
            continue

        email = email.strip()
        display_name = item.get("displayName") or email
        department = item.get("department") or None
        imported_role = azure_access.role_from_onprem_user(onprem_dn)
        user = by_email.get(email.lower())

        if user:
            changed = False
            if user.display_name != display_name:
                user.display_name = display_name
                changed = True
            if department and user.department != department:
                user.department = department
                changed = True
            if user.role == UserRole.TEACHER and imported_role != UserRole.TEACHER:
                user.role = imported_role
                changed = True
            if changed:
                updated += 1
            continue

        username = _unique_username(item.get("userPrincipalName") or email, usernames)
        user = User(
            username=username,
            email=email,
            display_name=display_name,
            department=department,
            role=imported_role,
            auth_provider="azure",
            is_active=True,
        )
        db.add(user)
        by_email[email.lower()] = user
        created += 1

    await db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "total": len(users)}


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
        "$select": "id,displayName,mail,userPrincipalName,department,accountEnabled,userType,onPremisesDistinguishedName",
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
