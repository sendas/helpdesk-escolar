import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LdapLoginRequest, TokenResponse
from app.services import ldap_auth, azure_auth, jwt_service
from app.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class DemoLoginRequest(BaseModel):
    role: str = "teacher"


async def get_or_create_user(db: AsyncSession, info: dict) -> User:
    result = await db.execute(select(User).where(User.username == info["username"]))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == info["email"]))
        user = result.scalar_one_or_none()

    if user:
        user.last_login = datetime.utcnow()
        if info.get("is_admin") and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
        elif info.get("role") and user.role != info["role"]:
            user.role = info["role"]
        await db.commit()
        return user

    role = info.get("role") or UserRole.TEACHER
    user = User(
        username=info["username"],
        email=info["email"],
        display_name=info["display_name"],
        role=UserRole.ADMIN if info.get("is_admin") else role,
        auth_provider=info["auth_provider"],
        last_login=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/ldap-login", response_model=TokenResponse)
async def ldap_login(data: LdapLoginRequest, db: AsyncSession = Depends(get_db)):
    user_info = ldap_auth.authenticate_ldap(data.username, data.password)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    user = await get_or_create_user(db, user_info)
    token = jwt_service.create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/azure-login")
async def azure_login(request: Request):
    if not settings.azure_ad_enabled or not settings.azure_client_id:
        raise HTTPException(status_code=400, detail="Azure AD not configured")
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    url = azure_auth.get_azure_login_url(state)
    return RedirectResponse(url)


@router.get("/azure-callback")
async def azure_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="State mismatch")
    user_info = await azure_auth.exchange_code_for_user(code)
    if not user_info:
        raise HTTPException(status_code=401, detail="Azure authentication failed")
    user = await get_or_create_user(db, user_info)
    token = jwt_service.create_access_token({"sub": str(user.id), "role": user.role})
    return RedirectResponse(f"{settings.frontend_url}/auth/callback#token={token}")


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(data: DemoLoginRequest, db: AsyncSession = Depends(get_db)):
    role_map = {"teacher": UserRole.TEACHER, "technician": UserRole.TECHNICIAN, "admin": UserRole.ADMIN}
    role = role_map.get(data.role, UserRole.TEACHER)
    label = {"teacher": "Docente Demo", "technician": "Técnico Demo", "admin": "Administrador Demo"}.get(data.role, "Demo")
    dept = {"teacher": "Línguas", "technician": "Serviços Informáticos", "admin": "Direção"}.get(data.role, "")

    username = f"demo_{data.role}"
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            username=username,
            email=f"{username}@demo.escola.pt",
            display_name=label,
            department=dept,
            role=role,
            auth_provider="demo",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = jwt_service.create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}
