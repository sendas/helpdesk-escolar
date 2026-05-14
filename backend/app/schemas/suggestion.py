from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SuggestionCreate(BaseModel):
    text: str


class SuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    created_at: datetime
    author_name: str
