from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.services import push_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PushSubscribePayload(BaseModel):
    endpoint: str
    keys: dict  # {p256dh: str, auth: str}


class PushUnsubscribePayload(BaseModel):
    endpoint: str


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    try:
        return {"public_key": push_service.get_public_key()}
    except Exception:
        raise HTTPException(status_code=500, detail="Não foi possível obter a chave VAPID")


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe(
    payload: PushSubscribePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p256dh = payload.keys.get("p256dh", "")
    auth = payload.keys.get("auth", "")
    if not payload.endpoint or not p256dh or not auth:
        raise HTTPException(status_code=400, detail="Dados de subscrição incompletos")

    existing = (
        await db.execute(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    ).scalar_one_or_none()

    if existing:
        existing.user_id = current_user.id
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        db.add(PushSubscription(
            user_id=current_user.id,
            endpoint=payload.endpoint,
            p256dh=p256dh,
            auth=auth,
        ))
    await db.commit()


@router.delete("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    payload: PushUnsubscribePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == payload.endpoint,
                PushSubscription.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()


@router.post("/test", status_code=status.HTTP_204_NO_CONTENT)
async def send_test_push(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subs = (
        await db.execute(select(PushSubscription).where(PushSubscription.user_id == current_user.id))
    ).scalars().all()
    if not subs:
        raise HTTPException(status_code=404, detail="Sem subscrições push ativas. Ative as notificações no browser primeiro.")
    await push_service.send_push_to_users(
        db,
        {current_user.id},
        "Teste de notificação",
        "As notificações push estão a funcionar correctamente!",
        "/dashboard",
    )
