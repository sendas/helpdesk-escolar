from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.category import CategoryRead


class KnowledgeArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    is_published: bool
    created_at: datetime
    updated_at: datetime
    category_id: int | None = None
    category: CategoryRead | None = None


class KnowledgeArticleCreate(BaseModel):
    title: str
    body: str
    category_id: int | None = None
    is_published: bool = True


class KnowledgeArticleUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    category_id: int | None = None
    is_published: bool | None = None
