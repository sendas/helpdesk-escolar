"""
Web Push notifications via VAPID.

Keys are generated automatically on first use and stored in /app/data/vapid_keys.json.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, NoEncryption, PublicFormat,
)
from py_vapid import Vapid
from pywebpush import webpush, WebPushException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

_KEYS_FILE = Path("/app/data/vapid_keys.json")
_VAPID_CLAIMS_SUB = "mailto:helpdesk@escola.local"

# In-memory cache so we only read the file once per process
_cached_keys: dict | None = None


def _generate_and_save_keys() -> dict:
    vapid = Vapid()
    vapid.generate_keys()
    private_pem = vapid.private_key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
    ).decode()
    pub_bytes = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    public_b64url = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    data = {"private_pem": private_pem, "public_b64url": public_b64url}
    _KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KEYS_FILE.write_text(json.dumps(data))
    return data


def _load_keys() -> dict:
    global _cached_keys
    if _cached_keys:
        return _cached_keys
    if _KEYS_FILE.exists():
        try:
            _cached_keys = json.loads(_KEYS_FILE.read_text())
            return _cached_keys
        except Exception:
            pass
    _cached_keys = _generate_and_save_keys()
    return _cached_keys


def get_public_key() -> str:
    return _load_keys()["public_b64url"]


def _send_sync(endpoint: str, p256dh: str, auth_key: str, payload: str, private_pem: str) -> bool:
    """Returns True if subscription should be removed (expired/invalid)."""
    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth_key}},
            data=payload.encode(),
            vapid_private_key=private_pem,
            vapid_claims={"sub": _VAPID_CLAIMS_SUB},
            timeout=10,
        )
        return False
    except WebPushException as exc:
        if exc.response is not None and exc.response.status_code in (404, 410):
            return True
        logger.debug("Push failed for %s: %s", endpoint[:60], exc)
        return False
    except Exception as exc:
        logger.debug("Push error: %s", exc)
        return False


async def send_push_to_users(db: AsyncSession, user_ids: set[int], title: str, body: str, url: str = "/") -> None:
    if not user_ids:
        return
    try:
        keys = _load_keys()
    except Exception:
        return

    subs = (
        await db.execute(select(PushSubscription).where(PushSubscription.user_id.in_(user_ids)))
    ).scalars().all()
    if not subs:
        return

    private_pem = keys["private_pem"]
    payload = json.dumps({"title": title, "body": body, "url": url})
    loop = asyncio.get_event_loop()

    results = await asyncio.gather(
        *[
            loop.run_in_executor(None, _send_sync, s.endpoint, s.p256dh, s.auth, payload, private_pem)
            for s in subs
        ],
        return_exceptions=True,
    )

    to_delete = [s.endpoint for s, r in zip(subs, results) if r is True]
    if to_delete:
        await db.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(to_delete)))
        await db.commit()


async def send_push_to_users_bg(user_ids: set[int], title: str, body: str, url: str = "/") -> None:
    """Fire-and-forget version that creates its own DB session."""
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            await send_push_to_users(db, user_ids, title, body, url)
    except Exception as exc:
        logger.debug("Background push error: %s", exc)
