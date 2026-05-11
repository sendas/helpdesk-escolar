from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_user, require_admin
from app.api.v1.settings import _read_settings
from app.models.knowledge import KnowledgeArticle
from app.models.user import User
from app.schemas.knowledge import KnowledgeArticleCreate, KnowledgeArticleRead, KnowledgeArticleUpdate

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeArticleRead])
async def list_articles(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    if not _read_settings().get("knowledge_enabled", True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Base de conhecimento inativa")
    result = await db.execute(
        select(KnowledgeArticle)
        .where(KnowledgeArticle.is_published.is_(True))
        .options(selectinload(KnowledgeArticle.category))
        .order_by(KnowledgeArticle.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/admin", response_model=list[KnowledgeArticleRead])
async def admin_list_articles(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    result = await db.execute(
        select(KnowledgeArticle)
        .options(selectinload(KnowledgeArticle.category))
        .order_by(KnowledgeArticle.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/admin", response_model=KnowledgeArticleRead, status_code=status.HTTP_201_CREATED)
async def create_article(data: KnowledgeArticleCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    article = KnowledgeArticle(**data.model_dump())
    db.add(article)
    await db.commit()
    return await _get_article(db, article.id)


@router.patch("/admin/{article_id}", response_model=KnowledgeArticleRead)
async def update_article(article_id: int, data: KnowledgeArticleUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    article = (await db.execute(select(KnowledgeArticle).where(KnowledgeArticle.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(article, key, value)
    article.updated_at = datetime.utcnow()
    await db.commit()
    return await _get_article(db, article.id)


@router.delete("/admin/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    article = (await db.execute(select(KnowledgeArticle).where(KnowledgeArticle.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    await db.delete(article)
    await db.commit()


async def _get_article(db: AsyncSession, article_id: int) -> KnowledgeArticle:
    result = await db.execute(
        select(KnowledgeArticle)
        .where(KnowledgeArticle.id == article_id)
        .options(selectinload(KnowledgeArticle.category))
    )
    return result.scalar_one()
