"""Small in-memory rate limiter (single backend process) for login and public forms."""
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status

_hits: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    # nginx (frontend container) sets X-Real-IP from the connection, after trusting only private proxies
    return (request.headers.get("x-real-ip") or (request.client.host if request.client else "") or "?").strip()


def _count(key: str, window: int) -> deque:
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    return q


def check(key: str, limit: int, window: int, message: str) -> None:
    """Refuse with 429 when `key` already reached `limit` hits within `window` seconds."""
    if len(_count(key, window)) >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)


def hit(key: str) -> None:
    _hits[key].append(time.monotonic())
    if len(_hits) > 20000:  # keep memory bounded
        for k in list(_hits)[:5000]:
            _hits.pop(k, None)


def reset(key: str) -> None:
    _hits.pop(key, None)
