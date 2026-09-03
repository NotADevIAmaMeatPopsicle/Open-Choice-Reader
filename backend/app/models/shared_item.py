from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


if "SharedItem" not in globals():
    class SharedItem(Base):
        __tablename__ = "shared_items"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        sender_user_id: Mapped[int] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=False
        )
        recipient_user_id: Mapped[int] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=False
        )
        item_type: Mapped[str] = mapped_column(String(32), nullable=False)
        source_item_id: Mapped[int] = mapped_column(Integer, nullable=False)
        item_label: Mapped[str] = mapped_column(String(255), nullable=False)
        message: Mapped[str | None] = mapped_column(Text, nullable=True)
        status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
        accepted_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=_utcnow, nullable=False
        )
        responded_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
