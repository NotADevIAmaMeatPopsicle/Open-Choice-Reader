from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


if "UserInvite" not in globals():
    class UserInvite(Base):
        __tablename__ = "user_invites"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
        created_by_user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), nullable=True
        )
        claimed_by_user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), nullable=True
        )
        display_name_hint: Mapped[str | None] = mapped_column(String(120), nullable=True)
        role_to_grant: Mapped[str] = mapped_column(
            String(32), default="member", nullable=False
        )
        expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
