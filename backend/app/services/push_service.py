"""
Web Push (RFC 8030 + RFC 8291 aes128gcm) usando apenas `cryptography` e `httpx`.
Sem dependências nativas externas (pywebpush / http-ece / py_vapid).

VAPID keys são geradas automaticamente em /app/data/vapid_keys.json na primeira execução.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import struct
from pathlib import Path

import httpx
from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDH, SECP256R1, EllipticCurvePrivateKey,
    generate_private_key, EllipticCurvePublicKey,
)
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, PublicFormat,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)

_KEYS_FILE = Path("/app/data/vapid_keys.json")
_VAPID_CLAIMS_SUB = "mailto:helpdesk@escola.local"
_cached_keys: dict | None = None


# ── VAPID key management ─────────────────────────────────────────────────────

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


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
        except Exception:
            pass
    _cached_keys = _generate_and_save_keys()
    return _cached_keys


def get_public_key() -> str:
    return _load_keys()["public_b64url"]


# ── VAPID JWT (ES256) ────────────────────────────────────────────────────────

def _make_vapid_jwt(endpoint: str, private_key: EllipticCurvePrivateKey) -> str:
    from urllib.parse import urlparse
    import time
    from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
    from cryptography.hazmat.primitives.hashes import SHA256 as _SHA256

    origin = "{0.scheme}://{0.netloc}".format(urlparse(endpoint))
    header = _b64u(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    payload = _b64u(json.dumps({
        "aud": origin,
        "exp": int(time.time()) + 12 * 3600,
        "sub": _VAPID_CLAIMS_SUB,
    }).encode())
    signing_input = f"{header}.{payload}".encode()

    from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
    der_sig = private_key.sign(signing_input, ECDSA(_SHA256()))
    r, s = decode_dss_signature(der_sig)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{header}.{payload}.{_b64u(raw_sig)}"


# ── RFC 8291 aes128gcm encryption ────────────────────────────────────────────

def _encrypt_payload(plaintext: bytes, p256dh_b64: str, auth_b64: str) -> tuple[bytes, bytes]:
    """Returns (ciphertext_with_header, sender_public_key_bytes)."""
    # Receiver public key
    receiver_pub_bytes = _b64u_decode(p256dh_b64)
    receiver_pub: EllipticCurvePublicKey = EllipticCurvePublicKey.from_encoded_point(SECP256R1(), receiver_pub_bytes)  # type: ignore[attr-defined]

    # Ephemeral sender key
    sender_priv: EllipticCurvePrivateKey = generate_private_key(SECP256R1())
    sender_pub_bytes = sender_priv.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

    # ECDH
    shared_secret = sender_priv.exchange(ECDH(), receiver_pub)

    auth_secret = _b64u_decode(auth_b64)
    salt = os.urandom(16)

    # PRK via HKDF-Extract (SHA-256)
    prk_info = b"WebPush: info\x00" + receiver_pub_bytes + sender_pub_bytes
    prk = HKDF(SHA256(), 32, auth_secret, prk_info).derive(shared_secret)

    # CEK and nonce
    cek = HKDF(SHA256(), 16, salt, b"Content-Encoding: aes128gcm\x00").derive(prk)
    nonce = HKDF(SHA256(), 12, salt, b"Content-Encoding: nonce\x00").derive(prk)

    # Pad payload (RFC 8291 §4: add \x02 delimiter)
    padded = plaintext + b"\x02"

    ciphertext = AESGCM(cek).encrypt(nonce, padded, None)

    # Build aes128gcm content-encoding header (RFC 8188)
    # salt(16) + rs(4, big-endian) + idlen(1) + sender_pub(65)
    rs = 4096
    header = salt + struct.pack(">I", rs) + bytes([len(sender_pub_bytes)]) + sender_pub_bytes

    return header + ciphertext, sender_pub_bytes


# ── Send a single push ───────────────────────────────────────────────────────

def _send_sync(endpoint: str, p256dh: str, auth_key: str, payload_json: str, private_pem: str) -> bool:
    """Returns True if subscription is expired/invalid and should be removed."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    private_key: EllipticCurvePrivateKey = load_pem_private_key(private_pem.encode(), password=None)  # type: ignore[assignment]
    pub_bytes = private_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

    try:
        body, _ = _encrypt_payload(payload_json.encode(), p256dh, auth_key)
    except Exception as exc:
        logger.debug("Push encryption error: %s", exc)
        return False

    jwt_token = _make_vapid_jwt(endpoint, private_key)
    vapid_pub = _b64u(pub_bytes)

    headers = {
        "Authorization": f"vapid t={jwt_token},k={vapid_pub}",
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": "86400",
    }

    try:
        resp = httpx.post(endpoint, content=body, headers=headers, timeout=10)
        if resp.status_code in (201, 202):
            logger.info("Push OK → %s", endpoint[:60])
            return False
        if resp.status_code in (404, 410):
            logger.info("Push subscription expired (%s) → removing %s", resp.status_code, endpoint[:60])
            return True
        if resp.status_code in (401, 403):
            logger.warning("Push VAPID auth error (%s) → removing stale subscription %s", resp.status_code, endpoint[:60])
            return True
        logger.warning("Push unexpected status %s → %s", resp.status_code, endpoint[:60])
        return False
    except Exception as exc:
        logger.warning("Push HTTP error: %s", exc)
        return False


# ── Public API ───────────────────────────────────────────────────────────────

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
    """Fire-and-forget: cria a sua própria sessão DB."""
    from app.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            await send_push_to_users(db, user_ids, title, body, url)
    except Exception as exc:
        logger.debug("Background push error: %s", exc)
