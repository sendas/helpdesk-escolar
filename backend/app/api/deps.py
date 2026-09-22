from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User, UserRole
from app.services.jwt_service import decode_token

bearer = HTTPBearer()


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
    if user.auth_provider == "demo":
        from app.api.v1.settings import _read_settings
        demo_role = user.username.removeprefix("demo_")
        app_settings = _read_settings()
        if not app_settings.get("demo_mode_enabled") or demo_role not in (app_settings.get("demo_profiles") or []):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="O modo demo foi desativado")
    return user


async def require_staff(user: User = Depends(get_current_user)) -> User:
    """Technician or Admin."""
    if user.role not in {UserRole.TECHNICIAN, UserRole.ADMIN} and not user.is_technician:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
