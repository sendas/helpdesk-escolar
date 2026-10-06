"""Restart the backend if its event loop stops answering.

A synchronous call that hangs inside an async handler (a network call without timeout, say) freezes the whole
server: no requests, no health checks, no background jobs — and Docker only marks the container "unhealthy",
it does not restart it. A thread outside the event loop notices the missing heartbeat, logs where the loop is
stuck and exits the process; `restart: unless-stopped` brings the container back up.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time
import traceback

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 5


def _limit() -> int:
    try:
        return int(os.environ.get("WATCHDOG_SECONDS", "180"))
    except ValueError:
        return 180


class Watchdog:
    def __init__(self) -> None:
        self.last_beat = time.monotonic()
        self._stop = threading.Event()
        self._task: asyncio.Task | None = None
        self._loop_thread_id: int | None = None

    async def _beat(self) -> None:
        while True:
            self.last_beat = time.monotonic()
            await asyncio.sleep(HEARTBEAT_SECONDS)

    def _watch(self, limit: int) -> None:
        while not self._stop.wait(HEARTBEAT_SECONDS):
            stalled = time.monotonic() - self.last_beat
            if stalled < limit:
                continue
            frame = sys._current_frames().get(self._loop_thread_id or 0)
            stack = "".join(traceback.format_stack(frame)) if frame else "(sem informação)"
            logger.critical("O servidor está bloqueado há %ss; a reiniciar. Bloqueado em:\n%s", int(stalled), stack)
            for handler in logging.getLogger().handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
            os._exit(1)

    def start(self) -> None:
        limit = _limit()
        if limit <= 0:
            return
        self._loop_thread_id = threading.get_ident()
        self.last_beat = time.monotonic()
        self._task = asyncio.create_task(self._beat())
        threading.Thread(target=self._watch, args=(limit,), name="watchdog", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
