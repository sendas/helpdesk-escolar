import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LdapLoginRequest, TokenResponse
from app.services import ldap_auth, azure_auth, jwt_service, passwords
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
        if info.get("onprem_dn") is not None:
            user.onprem_dn = info.get("onprem_dn")
        if info.get("onprem_path") is not None:
            user.onprem_path = info.get("onprem_path")
        if user.role_locked:
            pass
        elif info.get("is_admin") and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            user.role_source = "entra"
        elif info.get("role") and user.role != info["role"]:
            user.role = info["role"]
            user.role_source = "entra"
        await db.commit()
        return user

    role = info.get("role") or UserRole.TEACHER
    user = User(
        username=info["username"],
        email=info["email"],
        display_name=info["display_name"],
        role=UserRole.ADMIN if info.get("is_admin") else role,
        role_source="entra" if info["auth_provider"] == "azure" else info["auth_provider"],
        role_locked=False,
        onprem_dn=info.get("onprem_dn"),
        onprem_path=info.get("onprem_path"),
        auth_provider=info["auth_provider"],
        last_login=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/ldap-login", response_model=TokenResponse)
async def ldap_login(data: LdapLoginRequest, db: AsyncSession = Depends(get_db)):
    local_user = await authenticate_manual_user(db, data.username, data.password)
    if local_user:
        token = jwt_service.create_access_token({"sub": str(local_user.id), "role": local_user.role})
        return {"access_token": token, "token_type": "bearer"}

    user_info = ldap_auth.authenticate_ldap(data.username, data.password)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    user = await get_or_create_user(db, user_info)
    token = jwt_service.create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


async def authenticate_manual_user(db: AsyncSession, username_or_email: str, password: str) -> User | None:
    identifier = username_or_email.strip().lower()
    if not identifier:
        return None
    result = await db.execute(
        select(User).where(
            User.auth_provider == "manual",
            User.is_active.is_(True),
            or_(User.email.ilike(identifier), User.username == identifier),
        )
    )
    user = result.scalar_one_or_none()
    if not user or not passwords.verify_password(password, user.password_hash):
        return None
    user.last_login = datetime.utcnow()
    await db.commit()
    return user


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
