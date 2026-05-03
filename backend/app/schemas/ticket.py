from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.ticket import TicketStatus, TicketPriority
from app.schemas.user import UserRead
from app.schemas.category import CategoryRead
from app.schemas.school import SchoolRead


class TicketCreate(BaseModel):
    title: str
    description: str
    category_id: int
    school_id: int | None = None
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    assignee_id: int | None = None
    priority: TicketPriority | None = None


class CommentCreate(BaseModel):
    body: str
    is_internal: bool = False


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    is_internal: bool
    created_at: datetime
    author: UserRead


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime
    creator: UserRead
    assignee: UserRead | None = None
    category: CategoryRead
    school: SchoolRead | None = None
    comments: list[CommentRead] = []


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime
    creator: UserRead
    assignee: UserRead | None = None
    category: CategoryRead
    school: SchoolRead | None = None


class PaginatedTickets(BaseModel):
    items: list[TicketListItem]
    total: int
    page: int
    size: int
