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
_SCHOOL_HINTS = {"EQ": ("queiros", "queiroz", "eca"), "VG": ("vasco", "gama"), "PN": ("parque", "nacoes")}
LIST_NAMES = {"EQ": "Escola Secundária Eça de Queirós", "VG": "Escola Básica Vasco da Gama", "PN": "Escola Básica Parque das Nações"}


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def _match_school(key: str, schools: list[School]) -> School | None:
    for s in schools:
        if (s.short_name or "").strip().upper() == key:
            return s
    hints = _SCHOOL_HINTS.get(key, ())
    for s in schools:
        words = set(_fold(f"{s.name} {s.short_name}").replace("-", " ").split())
        if any(h in words for h in hints):
            return s
    return None


def seed_lists() -> dict[str, list[dict]]:
    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["school"], []).append(r)
    return out


async def import_list(db: AsyncSession, school_id: int, key: str) -> int:
    """Definições: load one of the lists (EQ, VG, PN) into a school, skipping rooms it already has (same code/name)."""
    rows = seed_lists().get(key, [])
    existing = {(r.code or "", r.name) for r in (await db.execute(select(Room).where(Room.school_id == school_id))).scalars()}
    added = 0
    for i, r in enumerate(rows):
        if (r.get("code") or "", r["name"]) in existing:
            continue
        db.add(Room(school_id=school_id, code=r.get("code"), name=r["name"], kind=r.get("kind") or "Sala de aula", sort=i))
        added += 1
    await db.commit()
    return added


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
