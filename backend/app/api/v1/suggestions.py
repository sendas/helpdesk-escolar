import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_admin
from app.models.suggestion import Suggestion
from app.models.user import User
from app.schemas.suggestion import SuggestionCreate, SuggestionRead
from app.api.v1.settings import _read_settings
from app.services.email_service import send_suggestion_notification
from app.config import settings as app_settings

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

_LISBON = timezone(timedelta(hours=1))


@router.post("", response_model=SuggestionRead, status_code=201)
async def create_suggestion(
    body: SuggestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suggestion = Suggestion(
        text=body.text.strip(),
        author_id=current_user.id,
        author_name=current_user.display_name,
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)

    recipients: list[str] = _read_settings().get("suggestion_emails", [])
    if recipients:
        created_lisbon = suggestion.created_at.replace(tzinfo=timezone.utc).astimezone(_LISBON)
        asyncio.create_task(send_suggestion_notification(
            recipients,
            {
                "author_name": suggestion.author_name,
                "text": suggestion.text,
                "created_at": created_lisbon.strftime("%d/%m/%Y %H:%M"),
                "suggestions_url": f"{app_settings.frontend_url.rstrip('/')}/suggestions",
            },
        ))

    return suggestion


@router.get("", response_model=list[SuggestionRead])
async def list_suggestions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Suggestion).order_by(Suggestion.created_at.desc()))
    return result.scalars().all()
