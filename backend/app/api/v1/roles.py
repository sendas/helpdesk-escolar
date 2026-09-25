import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, require_perm
from app.models.role import Role
from app.models.user import User, UserRole
from app.schemas.user import RoleCreate, RoleRead, RoleUpdate
from app.services import permissions

router = APIRouter(prefix="/roles", tags=["roles"])


def _clean_permissions(perms: list[str]) -> str:
    return ",".join(sorted({p for p in perms if p in permissions.ALL_PERMISSIONS}))


def _slug(label: str) -> str:
    text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")[:40] or "papel"


async def _users_of(db: AsyncSession, key: str):
    """Users whose effective papel is `key` (explicit role_key, or the default for their base role)."""
    query = select(User).where(User.role != UserRole.ADMIN)
    if key == "technician":
        query = query.where(or_(User.role_key == key, (User.role_key.is_(None)) & ((User.role == UserRole.TECHNICIAN) | User.is_technician.is_(True))))
    elif key in UserRole._value2member_map_:
        query = query.where(or_(User.role_key == key, (User.role_key.is_(None)) & (User.role == UserRole(key)) & User.is_technician.is_(False)))
    else:
        query = query.where(User.role_key == key)
    return (await db.execute(query)).scalars().all()


async def _read(db: AsyncSession, role: Role) -> RoleRead:
    if role.key == "admin":
        count = (await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN))).scalar_one()
    else:
        count = len(await _users_of(db, role.key))
    return RoleRead(
        key=role.key, label=role.label, icon=role.icon, color=role.color,
        permissions=[p for p in (role.permissions or "").split(",") if p],
        builtin=role.builtin, locked=role.key in permissions.LOCKED_KEYS, sort=role.sort, user_count=count,
    )


@router.get("/permissions")
async def list_permissions(_: User = Depends(get_current_user)):
    return permissions.PERMISSIONS


@router.get("", response_model=list[RoleRead])
async def list_roles(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    rows = (await db.execute(select(Role).order_by(Role.sort, Role.label))).scalars().all()
    return [await _read(db, r) for r in rows]


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(data: RoleCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("users.manage"))):
    label = data.label.strip()
    if not label:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indique o nome do papel.")
    base = key = _slug(label)
    n = 2
    while (await db.execute(select(Role).where(Role.key == key))).scalar_one_or_none():
        key = f"{base}_{n}"
        n += 1
    role = Role(key=key, label=label, icon=data.icon or "badge", color=data.color or "#64748B",
                permissions=_clean_permissions(data.permissions), builtin=False, sort=80)
    db.add(role)
    await db.commit()
    await permissions.load_roles(db)
    return await _read(db, role)


@router.patch("/{key}", response_model=RoleRead)
async def update_role(key: str, data: RoleUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("users.manage"))):
    role = (await db.execute(select(Role).where(Role.key == key))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Papel não encontrado.")
    if key in permissions.LOCKED_KEYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O papel de administrador não pode ser alterado.")
    if data.label is not None and data.label.strip():
        role.label = data.label.strip()
    if data.icon:
        role.icon = data.icon
    if data.color:
        role.color = data.color
    if data.permissions is not None:
        perms = set(data.permissions)
        if key == "technician":
            perms.add("tickets.manage")  # technicians always manage tickets
        role.permissions = _clean_permissions(list(perms))
    await db.commit()
    await permissions.load_roles(db)
    if data.permissions is not None:
        # Users of this papel start/stop managing tickets straight away
        for user in await _users_of(db, key):
            if not user.role_key:
                user.role_key = key
            permissions.sync_user_flags(user)
        await db.commit()
    return await _read(db, role)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(key: str, db: AsyncSession = Depends(get_db), _: User = Depends(require_perm("users.manage"))):
    role = (await db.execute(select(Role).where(Role.key == key))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Papel não encontrado.")
    if role.builtin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Os papéis base não podem ser apagados; pode alterar as permissões.")
    users = await _users_of(db, key)
    if users:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Há {len(users)} utilizador(es) com este papel. Mude-lhes o papel antes de o apagar.")
    await db.delete(role)
    await db.commit()
    await permissions.load_roles(db)
