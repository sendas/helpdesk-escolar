import asyncio
import logging
import re
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LdapLoginRequest, TokenResponse
from app.services import ldap_auth, azure_auth, jwt_service, passwords, email_service, rate_limit
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class DemoLoginRequest(BaseModel):
    role: str = "teacher"


class NoAccessContactRequest(BaseModel):
    profile: str = Field("docente", max_length=20)  # docente | nao_docente | aluno
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field("", max_length=200)
    student_number: str = Field("", max_length=20)
    year: str = Field("", max_length=10)
    class_name: str = Field("", max_length=10)
    phone: str = Field("", max_length=40)
    recruitment_group: str = Field("", max_length=200)
    school: str = Field("", max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)


async def get_or_create_user(db: AsyncSession, info: dict) -> User:
    result = await db.execute(select(User).where(User.username == info["username"]))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == info["email"]))
        user = result.scalar_one_or_none()

    if user:
        user.last_login = datetime.utcnow()
        if info.get("display_name"):
            user.directory_name = info["display_name"]
        if info.get("onprem_dn") is not None:
            user.onprem_dn = info.get("onprem_dn")
        if info.get("onprem_path") is not None:
            user.onprem_path = info.get("onprem_path")
        if info.get("department") is not None:
            user.department = info.get("department")
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
        directory_name=info["display_name"],
        department=info.get("department"),
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


_TOO_MANY_LOGINS = "Demasiadas tentativas de entrada. Aguarde 15 minutos e tente novamente."


@router.post("/ldap-login", response_model=TokenResponse)
async def ldap_login(data: LdapLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Brute-force protection: failed attempts are counted per address and per account
    ip_key = f"login-ip:{rate_limit.client_ip(request)}"
    user_key = f"login-user:{data.username.strip().lower()}"
    rate_limit.check(ip_key, 10, 900, _TOO_MANY_LOGINS)
    rate_limit.check(user_key, 20, 900, _TOO_MANY_LOGINS)

    local_user = await authenticate_manual_user(db, data.username, data.password)
    if local_user:
        rate_limit.reset(user_key)
        token = jwt_service.create_access_token({"sub": str(local_user.id), "role": local_user.role})
        return {"access_token": token, "token_type": "bearer"}

    user_info = await asyncio.to_thread(ldap_auth.authenticate_ldap, data.username, data.password)
    if not user_info:
        rate_limit.hit(ip_key)
        rate_limit.hit(user_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    rate_limit.reset(user_key)
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
            # exact match: ilike would treat "%" and "_" typed by the user as wildcards
            or_(func.lower(User.email) == identifier, User.username == identifier),
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
        raise HTTPException(status_code=400, detail="A entrada com Microsoft não está configurada.")
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    url = await azure_auth.get_azure_login_url(state)
    return RedirectResponse(url)


@router.get("/azure-callback")
async def azure_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if error or not code:
        # Microsoft sends the user back with ?error=... (consent missing, user not assigned to the app, ...)
        logging.getLogger(__name__).error("Login Microsoft devolveu erro: %s — %s", error, (error_description or "")[:300])
        raise HTTPException(status_code=401, detail="A Microsoft recusou a entrada. Contacte o administrador do helpdesk.")
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="O pedido de entrada expirou. Tente entrar novamente.")
    user_info = await azure_auth.exchange_code_for_user(code)
    if not user_info:
        raise HTTPException(status_code=401, detail="A autenticação Microsoft falhou. Tente novamente.")
    user = await get_or_create_user(db, user_info)
    token = jwt_service.create_access_token({"sub": str(user.id), "role": user.role})
    return RedirectResponse(f"{settings.frontend_url}/auth/callback#token={token}")


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(data: DemoLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from app.api.v1.settings import _read_settings

    demo_key = f"demo:{rate_limit.client_ip(request)}"
    rate_limit.check(demo_key, 30, 3600, "Demasiadas entradas em modo demo. Tente mais tarde.")
    rate_limit.hit(demo_key)
    app_settings = _read_settings()
    if not app_settings.get("demo_mode_enabled"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="O modo demo está desativado.")
    from app.api.v1.settings import DEMO_PROFILES
    if data.role not in DEMO_PROFILES or data.role not in (app_settings.get("demo_profiles") or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este perfil não está disponível no modo demo.")

    role_map = {"teacher": UserRole.TEACHER, "technician": UserRole.TECHNICIAN, "admin": UserRole.ADMIN}
    role = role_map[data.role]
    label = {"teacher": "Docente Demo", "technician": "Técnico Demo", "admin": "Administrador Demo"}[data.role]
    dept = {"teacher": "Línguas", "technician": "Serviços Informáticos", "admin": "Direção"}[data.role]

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
            is_technician=data.role == "technician",
            auth_provider="demo",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = jwt_service.create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/no-access-contact")
async def no_access_contact(data: NoAccessContactRequest, request: Request):
    from app.api.v1.settings import _read_settings

    contact_key = f"contact:{rate_limit.client_ip(request)}"
    rate_limit.check(contact_key, 5, 3600, "Já enviou várias mensagens. Aguarde um pouco antes de enviar outra.")
    rate_limit.hit(contact_key)
    app_settings = _read_settings()
    to_email = (app_settings.get("no_access_contact_email") or "").strip()
    if not to_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email de contacto não configurado. Peça a um administrador para o definir nas Configurações.")
    if not settings.mail_server:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envio de email não configurado no servidor.")

    contact_email = data.email.strip()
    profile = data.profile if data.profile in {"docente", "nao_docente", "aluno"} else "docente"
    if profile == "aluno":
        # Students often have no email: the card number, year, class and school identify them
        if not re.fullmatch(r"[aA]\d{3,8}", data.student_number.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indique o número do cartão de aluno (ex.: a12345).")
        if not data.year.strip() or not data.class_name.strip() or not data.school.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indique o ano, a turma e a escola.")
        if contact_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O email indicado não é válido.")
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Indique um email válido para podermos responder.")

    await email_service.send_no_access_contact(
        to_email,
        {
            "profile": {"docente": "Docente", "nao_docente": "Não docente", "aluno": "Aluno"}[profile],
            "is_student": profile == "aluno",
            "student_number": data.student_number.strip().lower(),
            "year": data.year.strip(),
            "class_name": data.class_name.strip().upper(),
            "name": data.name.strip(),
            "email": contact_email,
            "phone": data.phone.strip(),
            "recruitment_group": data.recruitment_group.strip(),
            "school": data.school.strip(),
            "message": data.message.strip(),
        },
    )
    return {"sent": True}
