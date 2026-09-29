"""Ratings of finished tickets and planned (recurring) maintenance tickets."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TicketRating(Base):
    """The requester's opinion once the ticket is resolved/closed (1 to 5 stars)."""
    __tablename__ = "ticket_ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    stars: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ScheduledTicket(Base):
    """Planned maintenance: a ticket created automatically every week/month/term/year."""
    __tablename__ = "scheduled_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id", ondelete="SET NULL"), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    frequency: Mapped[str] = mapped_column(String(20), default="monthly")  # weekly | monthly | quarterly | yearly
    next_run: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    last_ticket_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category = relationship("Category", lazy="selectin")
    school = relationship("School", lazy="selectin")
    assignee = relationship("User", foreign_keys=[assignee_id], lazy="selectin")
