"""Access statistics without slowing requests down: entries are kept in memory and written in batches every few
seconds (instead of one database write per request), and entries older than ACCESS_LOG_RETENTION_DAYS are removed."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, insert

logger = logging.getLogger(__name__)

FLUSH_SECONDS = 5
MAX_PENDING = 5000
ACCESS_LOG_RETENTION_DAYS = 180

_pending: list[dict] = []


def add(entry: dict) -> None:
    entry.setdefault("created_at", datetime.utcnow())
    if len(_pending) < MAX_PENDING:
        _pending.append(entry)


async def flush() -> int:
    if not _pending:
        return 0
    from app.database import AsyncSessionLocal
    from app.models.access_log import AccessLog
    batch = _pending[:]
    del _pending[:len(batch)]
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(insert(AccessLog), batch)
            await db.commit()
    except Exception:
        logger.warning("Não foi possível gravar %s registos de acesso", len(batch), exc_info=True)
    return len(batch)


async def prune() -> int:
    from app.database import AsyncSessionLocal
    from app.models.access_log import AccessLog
    cutoff = datetime.utcnow() - timedelta(days=ACCESS_LOG_RETENTION_DAYS)
    async with AsyncSessionLocal() as db:
        result = await db.execute(delete(AccessLog).where(AccessLog.created_at < cutoff))
        await db.commit()
    if result.rowcount:
        logger.info("Registo de acessos: %s entradas com mais de %s dias apagadas", result.rowcount, ACCESS_LOG_RETENTION_DAYS)
    return result.rowcount or 0


async def run_forever() -> None:
    rounds = 0
    while True:
        try:
            await asyncio.sleep(FLUSH_SECONDS)
            await flush()
            rounds += 1
            if rounds % (6 * 3600 // FLUSH_SECONDS) == 1:  # soon after start, then every 6 hours
                await prune()
        except asyncio.CancelledError:
            await flush()
            raise
        except Exception:
            logger.exception("Registo de acessos: falha na gravação periódica")
