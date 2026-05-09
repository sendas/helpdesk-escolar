"""
OneDrive for Business backup via Microsoft Graph API.

Permission required on the Azure AD app registration (application permission):
    Files.ReadWrite.All  → needs admin consent in Azure portal

Config fields (stored in backup_config.json):
    onedrive_enabled   : bool
    onedrive_user      : UPN / email of the target OneDrive owner (e.g. ti@escola.pt)
    onedrive_folder    : folder path inside that OneDrive (e.g. Backups/Helpdesk)
    onedrive_retention : how many files to keep per type (json / zip)
"""

from __future__ import annotations

import httpx
import msal
from pathlib import Path

from app.config import settings

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB — Graph API minimum chunk size


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_token() -> str:
    if not all([settings.azure_tenant_id, settings.azure_client_id, settings.azure_client_secret]):
        raise RuntimeError(
            "Azure AD não está configurado (AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET)"
        )
    app = msal.ConfidentialClientApplication(
        client_id=settings.azure_client_id,
        client_credential=settings.azure_client_secret,
        authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(
            f"Não foi possível obter token OneDrive: {result.get('error_description', result.get('error', 'unknown'))}"
        )
    return result["access_token"]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_file(file_path: str, user: str, folder: str) -> None:
    """Upload a local file to OneDrive. Chunked upload for files > 4 MB."""
    path = Path(file_path)
    size = path.stat().st_size
    token = _get_token()
    auth = {"Authorization": f"Bearer {token}"}
    folder = folder.strip("/")
    drive_root = f"{GRAPH_BASE}/users/{user}/drive/root:/{folder}/{path.name}"

    if size <= CHUNK_SIZE:
        url = f"{drive_root}:/content"
        with open(file_path, "rb") as f:
            content = f.read()
        resp = httpx.put(
            url,
            headers={**auth, "Content-Type": "application/octet-stream"},
            content=content,
            timeout=120,
        )
        resp.raise_for_status()
        return

    # --- Upload session for large files ---
    session_resp = httpx.post(
        f"{drive_root}:/createUploadSession",
        headers=auth,
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
        timeout=60,
    )
    session_resp.raise_for_status()
    upload_url = session_resp.json()["uploadUrl"]

    offset = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            end = offset + len(chunk) - 1
            chunk_resp = httpx.put(
                upload_url,
                headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{end}/{size}",
                },
                content=chunk,
                timeout=120,
            )
            if chunk_resp.status_code not in (200, 201, 202):
                chunk_resp.raise_for_status()
            offset += len(chunk)


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------

def _list_files(user: str, folder: str, prefix: str) -> list[dict]:
    folder = folder.strip("/")
    token = _get_token()
    url = f"{GRAPH_BASE}/users/{user}/drive/root:/{folder}:/children"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return [
        i for i in resp.json().get("value", [])
        if i.get("name", "").startswith(prefix) and "file" in i
    ]


def _delete_file(user: str, item_id: str) -> None:
    token = _get_token()
    httpx.delete(
        f"{GRAPH_BASE}/users/{user}/drive/items/{item_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ).raise_for_status()


def cleanup_remote(user: str, folder: str, prefix: str, retention: int) -> None:
    try:
        files = _list_files(user, folder, prefix)
        files.sort(key=lambda f: f.get("lastModifiedDateTime", ""), reverse=True)
        for old in files[retention:]:
            try:
                _delete_file(user, old["id"])
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_connection(user: str, folder: str) -> dict:
    folder = folder.strip("/")
    token = _get_token()
    url = f"{GRAPH_BASE}/users/{user}/drive/root:/{folder}/helpdesk-connection-test.txt:/content"
    resp = httpx.put(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
        content=b"helpdesk onedrive ok",
        timeout=60,
    )
    resp.raise_for_status()
    return {"ok": True, "user": user, "folder": folder}
