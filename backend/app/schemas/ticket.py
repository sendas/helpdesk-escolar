from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.ticket import TicketStatus, TicketPriority
from app.schemas.user import HelpdeskGroupRead, UserRead
from app.schemas.category import CategoryRead
from app.schemas.school import SchoolRead


class TicketCreate(BaseModel):
    title: str
    description: str
    category_id: int
    school_id: int
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    assignee_id: int | None = None
    group_id: int | None = None
    priority: TicketPriority | None = None


class TicketBulkUpdate(BaseModel):
    ids: list[int]
    status: TicketStatus | None = None
    assignee_id: int | None = None
    group_id: int | None = None
    priority: TicketPriority | None = None


class TicketBulkAction(BaseModel):
    ids: list[int]
    action: str


class CommentCreate(BaseModel):
    body: str
    is_internal: bool = False


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    author: UserRead


class CommentUpdate(BaseModel):
    body: str


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_name: str
    content_type: str
    size: int
    created_at: datetime


class TicketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    message: str
    created_at: datetime
    actor: UserRead | None = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    creator: UserRead
    assignee: UserRead | None = None
    group: HelpdeskGroupRead | None = None
    category: CategoryRead
    school: SchoolRead | None = None
    comments: list[CommentRead] = []
    attachments: list[AttachmentRead] = []
    events: list[TicketEventRead] = []


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    creator: UserRead
    assignee: UserRead | None = None
    group: HelpdeskGroupRead | None = None
    category: CategoryRead
    school: SchoolRead | None = None


class TicketRoutingRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None = None
    school_id: int | None = None
    group_id: int | None = None
    assignee_id: int | None = None
    priority: int = 100
    category: CategoryRead | None = None
    school: SchoolRead | None = None
    group: HelpdeskGroupRead | None = None
    assignee: UserRead | None = None


class TicketRoutingRuleCreate(BaseModel):
    category_id: int | None = None
    school_id: int | None = None
    group_id: int | None = None
    assignee_id: int | None = None
    priority: int = 100


class TicketRoutingRuleUpdate(BaseModel):
    category_id: int | None = None
    school_id: int | None = None
    group_id: int | None = None
    assignee_id: int | None = None
    priority: int | None = None


class PaginatedTickets(BaseModel):
    items: list[TicketListItem]
    total: int
    page: int
    size: int
