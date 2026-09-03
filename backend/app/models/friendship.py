from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


if "Friendship" not in globals():
    class Friendship(Base):
        __tablename__ = "friendships"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        requester_user_id: Mapped[int] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=False
        )
        addressee_user_id: Mapped[int] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=False
        )
        status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=_utcnow, nullable=False
        )
        responded_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
