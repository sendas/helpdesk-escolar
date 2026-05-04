from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    color: Mapped[str] = mapped_column(String(20), default="#1976D2")
    icon: Mapped[str] = mapped_column(String(50), default="help_outline")
    sla_hours: Mapped[int] = mapped_column(Integer, default=24)

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="category")
