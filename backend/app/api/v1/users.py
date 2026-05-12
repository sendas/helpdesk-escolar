from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user, require_admin, require_staff
from app.models.group import HelpdeskGroup
from app.models.user import User, UserRole
from app.schemas.user import (
    HelpdeskGroupCreate,
    HelpdeskGroupMembersUpdate,
    HelpdeskGroupRead,
    HelpdeskGroupUpdate,
    UserBulkUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services import azure_import, passwords

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    result = await db.execute(select(User).order_by(User.display_name))
    return result.scalars().all()


@router.get("/search", response_model=list[UserRead])
async def search_users(
    q: str = Query("", max_length=100),
    limit: int = Query(20, ge=1, le=50),
    technicians_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    term = q.strip()
    query = select(User).where(User.is_active.is_(True), User.id != current_user.id)
    if technicians_only:
        query = query.where(or_(User.role == UserRole.TECHNICIAN, User.is_technician.is_(True)))
    if term:
        like = f"%{term}%"
        query = query.where(
            or_(
                User.display_name.ilike(like),
                User.email.ilike(like),
                User.username.ilike(like),
            )
        )
    result = await db.execute(query.order_by(User.display_name).limit(limit))
    return result.scalars().all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_manual_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    display_name = data.display_name.strip()
    email = data.email.strip().lower()
    password = data.password.strip()
    if not display_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome é obrigatório")
    if "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email inválido")
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A palavra-passe deve ter pelo menos 8 caracteres")

    exists = await db.execute(select(User).where(User.email.ilike(email)))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um utilizador com esse email")

    username = (data.username or email.split("@", 1)[0]).strip().lower()
    if not username:
        username = email.split("@", 1)[0]
    username = await _unique_username(db, username)

    user = User(
        username=username,
        email=email,
        display_name=display_name,
        department=(data.department or "").strip() or None,
        role=data.role,
        role_source="manual",
        role_locked=True,
        auth_provider="manual",
        password_hash=passwords.hash_password(password),
        is_active=data.is_active,
        is_technician=data.is_technician or data.role == UserRole.TECHNICIAN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/import-azure")
async def import_users_from_azure(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        return await azure_import.import_azure_users(db)
    except azure_import.AzureImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/groups", response_model=list[HelpdeskGroupRead])
async def list_helpdesk_groups(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_staff),
):
    result = await db.execute(
        select(HelpdeskGroup)
        .options(selectinload(HelpdeskGroup.members))
        .order_by(HelpdeskGroup.name)
    )
    return result.scalars().all()


@router.post("/groups", response_model=HelpdeskGroupRead, status_code=status.HTTP_201_CREATED)
async def create_helpdesk_group(
    data: HelpdeskGroupCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group name is required")
    exists = await db.execute(select(HelpdeskGroup).where(HelpdeskGroup.name == name))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group already exists")
    group = HelpdeskGroup(name=name, description=(data.description or "").strip() or None)
    db.add(group)
    await db.commit()
    await db.refresh(group, ["members"])
    return group


@router.patch("/groups/{group_id}", response_model=HelpdeskGroupRead)
async def update_helpdesk_group(
    group_id: int,
    data: HelpdeskGroupUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(HelpdeskGroup)
        .where(HelpdeskGroup.id == group_id)
        .options(selectinload(HelpdeskGroup.members))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group name is required")
        group.name = name
    if data.description is not None:
        group.description = data.description.strip() or None
    await db.commit()
    await db.refresh(group)
    return group


@router.put("/groups/{group_id}/members", response_model=HelpdeskGroupRead)
async def update_helpdesk_group_members(
    group_id: int,
    data: HelpdeskGroupMembersUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(HelpdeskGroup)
        .where(HelpdeskGroup.id == group_id)
        .options(selectinload(HelpdeskGroup.members))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    members = []
    if data.user_ids:
        members = (await db.execute(select(User).where(User.id.in_(data.user_ids)))).scalars().all()
    group.members = list(members)
    await db.commit()
    result = await db.execute(
        select(HelpdeskGroup)
        .where(HelpdeskGroup.id == group_id)
        .options(selectinload(HelpdeskGroup.members))
    )
    return result.scalar_one()


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_helpdesk_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(
        select(HelpdeskGroup)
        .where(HelpdeskGroup.id == group_id)
        .options(selectinload(HelpdeskGroup.members))
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    group.members = []
    await db.delete(group)
    await db.commit()


@router.patch("/bulk", response_model=list[UserRead])
async def bulk_update_users(
    data: UserBulkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if not data.ids:
        return []
    result = await db.execute(select(User).where(User.id.in_(data.ids)))
    users = result.scalars().all()
    for user in users:
        if data.role is not None:
            user.role = data.role
            user.role_source = "manual"
            user.role_locked = True
            if data.role == UserRole.TECHNICIAN:
                user.is_technician = True
        if data.is_technician is not None:
            user.is_technician = data.is_technician
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.role_locked is not None:
            user.role_locked = data.role_locked
            user.role_source = "manual" if data.role_locked else "entra"
    await db.commit()
    return users


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if data.role is not None:
        user.role = data.role
        user.role_source = "manual"
        user.role_locked = True
        if data.role == UserRole.TECHNICIAN:
            user.is_technician = True
    if data.is_technician is not None:
        user.is_technician = data.is_technician
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.department is not None:
        user.department = data.department.strip() or None
    if data.role_locked is not None:
        user.role_locked = data.role_locked
        user.role_source = "manual" if data.role_locked else "entra"
    await db.commit()
    await db.refresh(user)
    return user


async def _unique_username(db: AsyncSession, base: str) -> str:
    candidate = base
    suffix = 2
    while True:
        exists = await db.execute(select(User).where(User.username == candidate))
        if not exists.scalar_one_or_none():
            return candidate
        candidate = f"{base}{suffix}"
        suffix += 1
