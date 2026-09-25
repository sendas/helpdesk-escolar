from contextvars import ContextVar
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.services.jwt_service import decode_token

bearer = HTTPBearer()

# Set for the current request when the caller is a demo account (read by email_service).
acting_as_demo: ContextVar[bool] = ContextVar("acting_as_demo", default=False)
# Id of the authenticated user for the current request (reminders are only serialised for their author).
current_viewer_id: ContextVar[int | None] = ContextVar("current_viewer_id", default=None)
# Whether that user is a technician/admin (internal notes are only serialised for staff).
current_viewer_is_staff: ContextVar[bool] = ContextVar("current_viewer_is_staff", default=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    current_viewer_id.set(user.id)
    current_viewer_is_staff.set(user.role in {UserRole.TECHNICIAN, UserRole.ADMIN} or user.is_technician)
    if user.auth_provider == "demo":
        from app.api.v1.settings import _read_settings
        demo_role = user.username.removeprefix("demo_")
        app_settings = _read_settings()
        if not app_settings.get("demo_mode_enabled") or demo_role not in (app_settings.get("demo_profiles") or []):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="O modo demo foi desativado")
        acting_as_demo.set(True)
    return user


def require_perm(*perms: str):
    """Dependency: the user needs at least one of these permissions (see app.services.permissions)."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        from app.services.permissions import permissions_for
        if not permissions_for(user) & set(perms):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não tem permissão para esta ação.")
        return user
    return _check


async def require_staff(user: User = Depends(get_current_user)) -> User:
    """Technician or Admin."""
    if user.role not in {UserRole.TECHNICIAN, UserRole.ADMIN} and not user.is_technician:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
