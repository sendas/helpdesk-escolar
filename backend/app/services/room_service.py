"""Rooms of each school: the list that comes with the app (app/seed/rooms.json, from the agrupamento's list of
spaces) and the check for tickets already opened for the same room."""
from __future__ import annotations

import json
import logging
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.school import School

logger = logging.getLogger(__name__)

SEED_FILE = Path(__file__).resolve().parent.parent / "seed" / "rooms.json"
RECENT_DAYS = 7
# How each school of the list is recognised among the schools set up in the app
_SCHOOL_HINTS = {"EQ": ("eça de queirós", "eca de queiros"), "VG": ("vasco da gama",), "PN": ("parque das nações", "parque das nacoes")}


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def _match_school(key: str, schools: list[School]) -> School | None:
    for s in schools:
        if (s.short_name or "").strip().upper() == key:
            return s
    hints = [_fold(h) for h in _SCHOOL_HINTS.get(key, ())]
    for s in schools:
        if any(h in _fold(s.name) for h in hints):
            return s
    return None


async def seed_rooms(db: AsyncSession) -> int:
    """Load the list of spaces for each school of the list (EQ, VG, PN) that has no rooms yet. A school that already
    has rooms is left alone (they are then edited in Definições), so a room removed there does not come back."""
    try:
        rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Lista de salas em falta ou inválida: %s", SEED_FILE)
        return 0
    schools = list((await db.execute(select(School))).scalars())
    with_rooms = set((await db.execute(select(Room.school_id).distinct())).scalars())
    added = 0
    for key in dict.fromkeys(r["school"] for r in rows):
        school = _match_school(key, schools)
        if not school:
            logger.warning("Lista de salas: nenhuma escola corresponde a %s", key)
            continue
        if school.id in with_rooms:
            continue
        for i, r in enumerate(rows):
            if r["school"] == key:
                db.add(Room(school_id=school.id, code=r.get("code"), name=r["name"], kind=r.get("kind") or "Sala de aula", sort=i))
                added += 1
        with_rooms.add(school.id)
    if added:
        await db.commit()
        logger.info("Salas carregadas: %s", added)
    return added


async def recent_tickets(db: AsyncSession, room_id: int, days: int = RECENT_DAYS) -> list:
    from app.models.ticket import Ticket
    since = datetime.utcnow() - timedelta(days=days)
    from sqlalchemy.orm import selectinload
    return list((await db.execute(
        select(Ticket).where(Ticket.room_id == room_id, Ticket.created_at >= since)
        .options(selectinload(Ticket.assignees), selectinload(Ticket.watchers))
        .order_by(Ticket.created_at.desc())
    )).scalars())
