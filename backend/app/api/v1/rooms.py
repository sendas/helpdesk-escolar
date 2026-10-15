from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_perm
from app.models.room import Room
from app.models.school import School
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.school import RoomRead, RoomWrite
from app.services import room_service

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomRead])
async def list_rooms(school_id: int | None = None, all: bool = Query(False), db: AsyncSession = Depends(get_db),
                     _: User = Depends(get_current_user)):
    """The rooms of a school, in the order of the agrupamento's list (inactive ones only with all=true)."""
    q = select(Room).order_by(Room.school_id, Room.sort, Room.id)
    if school_id is not None:
        q = q.where(Room.school_id == school_id)
    if not all:
        q = q.where(Room.active.is_(True))
    return list((await db.execute(q)).scalars())


@router.get("/lists")
async def room_lists(_: User = Depends(require_perm("settings.manage"))):
    """The lists of spaces that come with the app, to load into a school."""
    return [{"key": k, "name": room_service.LIST_NAMES.get(k, k), "count": len(v)} for k, v in room_service.seed_lists().items()]


class RoomImport(BaseModel):
    school_id: int
    key: str


@router.post("/import")
async def import_rooms(data: RoomImport, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("settings.manage"))):
    await _check_school(db, data.school_id)
    if data.key not in room_service.seed_lists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lista de salas desconhecida.")
    return {"added": await room_service.import_list(db, data.school_id, data.key)}


@router.get("/{room_id}/recent")
async def room_recent_tickets(room_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Tickets opened for this room in the last days: shown before someone opens another one."""
    from app.api.v1.tickets import recent_ticket_info
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")
    tickets = await room_service.recent_tickets(db, room_id)
    return {"days": room_service.RECENT_DAYS, "room": room.label, "tickets": [recent_ticket_info(t, current_user) for t in tickets]}


async def _check_school(db: AsyncSession, school_id: int) -> None:
    if not await db.get(School, school_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escola inválida.")


@router.post("", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(data: RoomWrite, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("settings.manage"))):
    await _check_school(db, data.school_id)
    if not data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indique o nome da sala.")
    last = (await db.execute(select(Room.sort).where(Room.school_id == data.school_id).order_by(Room.sort.desc()).limit(1))).scalar_one_or_none()
    room = Room(school_id=data.school_id, code=(data.code or "").strip() or None, name=data.name.strip(),
                kind=data.kind.strip() or "Sala de aula", active=data.active, sort=(last or 0) + 1)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.put("/{room_id}", response_model=RoomRead)
async def update_room(room_id: int, data: RoomWrite, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("settings.manage"))):
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")
    if not data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indique o nome da sala.")
    room.code = (data.code or "").strip() or None
    room.name = data.name.strip()
    room.kind = data.kind.strip() or "Sala de aula"
    room.active = data.active
    await db.commit()
    await db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("settings.manage"))):
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala não encontrada.")
    # Tickets keep their history: they just lose the link to the room
    await db.execute(update(Ticket).where(Ticket.room_id == room_id).values(room_id=None))
    await db.delete(room)
    await db.commit()
