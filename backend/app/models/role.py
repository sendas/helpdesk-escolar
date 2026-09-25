from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Role(Base):
    """Editable role (papel): a label plus a set of permissions from app.services.permissions.PERMISSIONS."""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(50), default="badge")
    color: Mapped[str] = mapped_column(String(20), default="#64748B")
    permissions: Mapped[str] = mapped_column(Text, default="")
    builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=100)
