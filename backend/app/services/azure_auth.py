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
            "https://graph.microsoft.com/v1.0/me?$select=displayName,mail,userPrincipalName,onPremisesDistinguishedName",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            return None
        profile = resp.json()

    email = profile.get("mail") or profile.get("userPrincipalName", "")
    onprem_dn = profile.get("onPremisesDistinguishedName")
    if not azure_access.is_allowed_onprem_user(onprem_dn):
        return None

    role = azure_access.role_from_onprem_user(onprem_dn)
    is_admin = await _check_admin_group(access_token) or azure_access.is_email_admin(email) or role.value == "admin"

    return {
        "username": (profile.get("userPrincipalName") or "").split("@")[0],
        "email": email,
        "display_name": profile.get("displayName", ""),
        "is_admin": is_admin,
        "role": role,
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
