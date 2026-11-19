from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccessRequest(Base):
    """A request from the "Não tenho acesso ao mail institucional" form: kept in the helpdesk and answered there."""
    __tablename__ = "access_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    profile: Mapped[str] = mapped_column(String(20), default="docente")  # docente | nao_docente | aluno
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    student_number: Mapped[str] = mapped_column(String(20), default="")
    year: Mapped[str] = mapped_column(String(10), default="")
    class_name: Mapped[str] = mapped_column(String(10), default="")
    school: Mapped[str] = mapped_column(String(200), default="")
    recruitment_group: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(Text)
    # new: waiting for the team · answered: waiting for the person · closed
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    handled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Imported from an earlier alert email ("Importar pedidos anteriores"): its Message-ID, to import it only once
    source_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True, unique=True)

    handled_by: Mapped["User"] = relationship("User", lazy="selectin")
    messages: Mapped[list["AccessRequestMessage"]] = relationship(
        "AccessRequestMessage", back_populates="request", lazy="selectin", order_by="AccessRequestMessage.created_at",
        cascade="all, delete-orphan")


class AccessRequestMessage(Base):
    """An answer by email, a phone call or an internal note from the team, or a reply by email from the person."""
    __tablename__ = "access_request_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("access_requests.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # None: the person, by email
    kind: Mapped[str] = mapped_column(String(20), default="email")  # email | phone | note | inbound
    body: Mapped[str] = mapped_column(Text)
    message_id: Mapped[str | None] = mapped_column(String(500), nullable=True, unique=True)  # inbound emails, to skip repeats
    sent_ok: Mapped[int] = mapped_column(Integer, default=1)

    request: Mapped[AccessRequest] = relationship("AccessRequest", back_populates="messages")
    author: Mapped["User"] = relationship("User", lazy="selectin")
