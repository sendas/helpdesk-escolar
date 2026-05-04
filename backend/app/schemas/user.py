from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    display_name: str
    department: str | None = None
    role: UserRole
    role_source: str = "entra"
    role_locked: bool = False
    onprem_path: str | None = None
    auth_provider: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    department: str | None = None
    role_locked: bool | None = None


class UserBulkUpdate(BaseModel):
    ids: list[int]
    role: UserRole | None = None
    is_active: bool | None = None
    role_locked: bool | None = None
