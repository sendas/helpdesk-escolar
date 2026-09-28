from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Reaction(Base):
    """Emoji reaction by a user to a ticket reply ("comment") or a chat message ("chat")."""
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("target_type", "target_id", "user_id", "emoji", name="uq_reaction"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(20), index=True)
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    emoji: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", lazy="selectin")
