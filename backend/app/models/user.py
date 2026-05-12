import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserRole(str, enum.Enum):
    TEACHER = "teacher"
    NON_TEACHING = "non_teaching"
    SECRETARY = "secretary"
    TECHNICIAN = "technician"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.TEACHER)
    role_source: Mapped[str] = mapped_column(String(20), default="entra")
    role_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    onprem_dn: Mapped[str | None] = mapped_column(String(500), nullable=True)
    onprem_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="ldap")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", foreign_keys="Ticket.creator_id", back_populates="creator"
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", foreign_keys="Ticket.assignee_id", back_populates="assignee"
    )
    assigned_many_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        secondary="ticket_assignees",
        back_populates="assignees",
    )
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")
    helpdesk_groups: Mapped[list["HelpdeskGroup"]] = relationship(
        "HelpdeskGroup",
        secondary="helpdesk_group_members",
        back_populates="members",
    )
    watched_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        secondary="ticket_watchers",
        back_populates="watchers",
    )
