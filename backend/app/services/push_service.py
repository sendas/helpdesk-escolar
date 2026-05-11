"""
Web Push notifications.

VAPID keys are generated automatically in /app/data/vapid_keys.json and must stay
persisted between deploys, otherwise browser subscriptions need to be recreated.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, EllipticCurvePrivateKey, generate_private_key
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

_KEYS_FILE = Path("/app/data/vapid_keys.json")
_cached_keys: dict | None = None


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _generate_and_save_keys() -> dict:
    key: EllipticCurvePrivateKey = generate_private_key(SECP256R1())
    private_pem = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()).decode()
    pub_bytes = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    data = {"private_pem": private_pem, "public_b64url": _b64u(pub_bytes)}
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
        except Exception as exc:
            logger.warning("Could not read VAPID keys, generating new ones: %s", exc)
    _cached_keys = _generate_and_save_keys()
    return _cached_keys


def get_public_key() -> str:
    return _load_keys()["public_b64url"]


def _vapid_subject() -> str:
    subject = (settings.push_vapid_subject or "").strip()
    if subject.startswith(("mailto:", "https://")):
        return subject
    if settings.mail_from and "@" in settings.mail_from:
        return f"mailto:{settings.mail_from}"
    return "mailto:helpdesk@techpro.pt"


def _send_sync(endpoint: str, p256dh: str, auth_key: str, payload_json: str, private_pem: str) -> bool:
    """Returns True only when the browser subscription is definitely expired."""
    subscription_info = {
        "endpoint": endpoint,
        "keys": {
            "p256dh": p256dh,
            "auth": auth_key,
        },
    }
    try:
        webpush(
            subscription_info=subscription_info,
            data=payload_json,
            vapid_private_key=private_pem,
            vapid_claims={"sub": _vapid_subject()},
            ttl=86400,
        )
        logger.info("Push OK -> %s", endpoint[:80])
        return False
    except WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (404, 410):
            logger.info("Push subscription expired (%s) -> removing %s", status_code, endpoint[:80])
            return True
        logger.warning("Push failed (%s) for %s: %s", status_code or "no-status", endpoint[:80], exc)
        return False
    except Exception as exc:
        logger.warning("Push unexpected error for %s: %s", endpoint[:80], exc)
        return False


async def send_push_to_users(db: AsyncSession, user_ids: set[int], title: str, body: str, url: str = "/") -> None:
    if not user_ids:
        return
    try:
        keys = _load_keys()
    except Exception as exc:
        logger.warning("Push skipped: could not load VAPID keys: %s", exc)
        return

    subs = (
        await db.execute(select(PushSubscription).where(PushSubscription.user_id.in_(user_ids)))
    ).scalars().all()
    if not subs:
        logger.info("Push skipped: no subscriptions for users %s", sorted(user_ids))
        return

    private_pem = keys["private_pem"]
    payload = json.dumps({"title": title, "body": body, "url": url})
    loop = asyncio.get_event_loop()

    results = await asyncio.gather(
        *[
            loop.run_in_executor(None, _send_sync, sub.endpoint, sub.p256dh, sub.auth, payload, private_pem)
            for sub in subs
        ],
        return_exceptions=True,
    )

    to_delete = [sub.endpoint for sub, result in zip(subs, results) if result is True]
    if to_delete:
        await db.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(to_delete)))
        await db.commit()


async def send_push_to_users_bg(user_ids: set[int], title: str, body: str, url: str = "/") -> None:
    """Fire-and-forget: creates its own DB session."""
    from app.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            await send_push_to_users(db, user_ids, title, body, url)
    except Exception as exc:
        logger.warning("Background push error: %s", exc)
