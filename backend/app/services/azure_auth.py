import msal
import httpx
from app.config import settings
from app.services import azure_access


def get_msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
    )


def get_azure_login_url(state: str) -> str:
    app = get_msal_app()
    return app.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=settings.azure_redirect_uri,
        state=state,
    )


async def exchange_code_for_user(code: str) -> dict | None:
    app = get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=["User.Read"],
        redirect_uri=settings.azure_redirect_uri,
    )
    if "error" in result:
        return None

    access_token = result["access_token"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.microsoft.com/v1.0/me?$select=displayName,mail,userPrincipalName,proxyAddresses,otherMails,department,onPremisesDistinguishedName",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            return None
        profile = resp.json()

    email = _preferred_email(profile)
    onprem_dn = profile.get("onPremisesDistinguishedName")
    department = profile.get("department")
    if not azure_access.is_allowed_directory_user(onprem_dn, department):
        return None

    role = azure_access.role_from_directory_user(onprem_dn, department)
    is_admin = await _check_admin_group(access_token) or azure_access.is_email_admin(email) or role.value == "admin"

    return {
        "username": (profile.get("userPrincipalName") or "").split("@")[0],
        "email": email,
        "display_name": profile.get("displayName", ""),
        "department": department,
        "is_admin": is_admin,
        "role": role,
        "onprem_dn": onprem_dn,
        "onprem_path": azure_access.dn_to_path(onprem_dn) or None,
        "auth_provider": "azure",
    }


async def _check_admin_group(access_token: str) -> bool:
    if not settings.azure_admin_group_id:
        return False
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.microsoft.com/v1.0/me/memberOf/{settings.azure_admin_group_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return resp.status_code == 200


def _preferred_email(profile: dict) -> str:
    candidates: list[str] = []
    if profile.get("mail"):
        candidates.append(profile["mail"])
    proxy_addresses = profile.get("proxyAddresses") or []
    candidates.extend(addr[5:] for addr in proxy_addresses if isinstance(addr, str) and addr.startswith("SMTP:"))
    candidates.extend(addr[5:] for addr in proxy_addresses if isinstance(addr, str) and addr.startswith("smtp:"))
    candidates.extend(profile.get("otherMails") or [])
    if profile.get("userPrincipalName"):
        candidates.append(profile["userPrincipalName"])

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
