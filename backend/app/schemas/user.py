from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    display_name: str
    department: str | None = None
    role: UserRole
    is_technician: bool = False
    role_source: str = "entra"
    role_locked: bool = False
    onprem_path: str | None = None
    auth_provider: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_technician: bool | None = None
    is_active: bool | None = None
    department: str | None = None
    role_locked: bool | None = None


class UserCreate(BaseModel):
    display_name: str
    email: str
    password: str
    role: UserRole = UserRole.TEACHER
    is_technician: bool = False
    department: str | None = None
    is_active: bool = True
    username: str | None = None


class UserBulkUpdate(BaseModel):
    ids: list[int]
    role: UserRole | None = None
    is_technician: bool | None = None
    is_active: bool | None = None
    role_locked: bool | None = None


class HelpdeskGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime
    members: list[UserRead] = Field(default_factory=list)


class HelpdeskGroupCreate(BaseModel):
    name: str
    description: str | None = None


class HelpdeskGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class HelpdeskGroupMembersUpdate(BaseModel):
    user_ids: list[int]
