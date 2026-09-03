from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


if "AuthSession" not in globals():
    class AuthSession(Base):
        __tablename__ = "auth_sessions"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
        session_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
        last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
        expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        created_by_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
        user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
