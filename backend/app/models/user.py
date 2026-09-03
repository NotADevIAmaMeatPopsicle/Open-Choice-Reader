from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


if "User" not in globals():
    class User(Base):
        __tablename__ = "users"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
        display_name: Mapped[str] = mapped_column(String(120))
        password_hash: Mapped[str] = mapped_column(String(255))
        role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
        status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
        )
        last_login_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
