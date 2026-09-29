import enum
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SAEnum, Boolean, Column, Table, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


ticket_watchers = Table(
    "ticket_watchers",
    Base.metadata,
    Column("ticket_id", ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


ticket_assignees = Table(
    "ticket_assignees",
    Base.metadata,
    Column("ticket_id", ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


# Private message to several people: everyone listed here (and the author) sees it. Comment.private_to_id keeps the
# first recipient and marks the comment as private.
comment_private_recipients = Table(
    "comment_private_recipients",
    Base.metadata,
    Column("comment_id", ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(SAEnum(TicketStatus), default=TicketStatus.OPEN)
    priority: Mapped[TicketPriority] = mapped_column(SAEnum(TicketPriority), default=TicketPriority.MEDIUM)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # When the ticket was resolved or closed (cleared if it is reopened); used by the statistics
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    creator_email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_via_email: Mapped[bool] = mapped_column(Boolean, default=False)

    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("helpdesk_groups.id"), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True)

    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id], back_populates="created_tickets")
    assignee: Mapped["User | None"] = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tickets")
    assignees: Mapped[list["User"]] = relationship(
        "User",
        secondary=ticket_assignees,
        back_populates="assigned_many_tickets",
    )
    group: Mapped["HelpdeskGroup | None"] = relationship("HelpdeskGroup")
    category: Mapped["Category"] = relationship("Category", back_populates="tickets")
    school: Mapped["School | None"] = relationship("School", back_populates="tickets")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="ticket", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan")
    watchers: Mapped[list["User"]] = relationship(
        "User",
        secondary=ticket_watchers,
        back_populates="watched_tickets",
    )
    events: Mapped[list["TicketEvent"]] = relationship(
        "TicketEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.created_at.desc()",
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Private reminder for the author of an internal note (stored in UTC)
    remind_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Private message: only the author and this user can see the comment
    private_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # People mentioned with @Nome (comma-separated user ids); they are notified
    mention_ids: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="comments")
    author: Mapped["User"] = relationship("User", back_populates="comments", foreign_keys=[author_id])
    private_to: Mapped["User"] = relationship("User", foreign_keys=[private_to_id], lazy="selectin")
    private_recipients: Mapped[list["User"]] = relationship("User", secondary=comment_private_recipients, lazy="selectin")

    def private_participants(self) -> set[int]:
        """Everyone who sees this private message (empty set for a normal comment)."""
        if not self.private_to_id:
            return set()
        return {self.author_id, self.private_to_id, *(u.id for u in self.private_recipients)}


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="events")
    actor: Mapped["User | None"] = relationship("User")


class TicketRoutingRule(Base):
    __tablename__ = "ticket_routing_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("helpdesk_groups.id"), nullable=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    priority: Mapped[int] = mapped_column(default=100)

    category: Mapped["Category | None"] = relationship("Category")
    school: Mapped["School | None"] = relationship("School")
    group: Mapped["HelpdeskGroup | None"] = relationship("HelpdeskGroup")
    assignee: Mapped["User | None"] = relationship("User")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="attachments")
    uploaded_by: Mapped["User"] = relationship("User")


class TicketReminder(Base):
    """Private reminder set by a user on a ticket ("Lembrar-me deste ticket"), independent of any reply."""
    __tablename__ = "ticket_reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # UTC
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ticket: Mapped["Ticket"] = relationship("Ticket")
    user: Mapped["User"] = relationship("User")


class TicketView(Base):
    """When a user last opened a ticket ("lido/não lido" in Os meus tickets)."""
    __tablename__ = "ticket_views"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # "Marcar como não lido"
    marked_unread: Mapped[bool] = mapped_column(Boolean, default=False)


class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    sender_email: Mapped[str] = mapped_column(String(200))
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


@event.listens_for(Ticket.status, "set", active_history=True)
def _track_resolved_at(target: Ticket, value, oldvalue, _initiator) -> None:
    """Every way a ticket changes state (page, email, inactivity, bulk) passes here."""
    done = (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    if value in done and oldvalue not in done:
        target.resolved_at = datetime.utcnow()
    elif value not in done:
        target.resolved_at = None
