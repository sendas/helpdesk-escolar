from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    short_name: Mapped[str] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="school")
