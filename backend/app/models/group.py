from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


helpdesk_group_members = Table(
    "helpdesk_group_members",
    Base.metadata,
    Column("group_id", ForeignKey("helpdesk_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class HelpdeskGroup(Base):
    __tablename__ = "helpdesk_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    members: Mapped[list["User"]] = relationship(
        "User",
        secondary=helpdesk_group_members,
        back_populates="helpdesk_groups",
    )
