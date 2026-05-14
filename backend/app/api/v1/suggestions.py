from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_admin
from app.models.suggestion import Suggestion
from app.models.user import User
from app.schemas.suggestion import SuggestionCreate, SuggestionRead

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


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
    return suggestion


@router.get("", response_model=list[SuggestionRead])
async def list_suggestions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Suggestion).order_by(Suggestion.created_at.desc()))
    return result.scalars().all()
