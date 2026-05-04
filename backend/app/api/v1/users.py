from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, require_admin
from app.models.user import User
from app.schemas.user import UserBulkUpdate, UserRead, UserUpdate
from app.services import azure_import

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.display_name))
    return result.scalars().all()


@router.post("/import-azure")
async def import_users_from_azure(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        return await azure_import.import_azure_users(db)
    except azure_import.AzureImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role_locked is not None:
        user.role_locked = data.role_locked
        user.role_source = "manual" if data.role_locked else "entra"
    await db.commit()
    await db.refresh(user)
    return user
