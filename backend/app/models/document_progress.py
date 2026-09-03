from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


if "DocumentProgress" not in globals():
    class DocumentProgress(Base):
        __tablename__ = "document_progress"
        __table_args__ = {"extend_existing": True}

        document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), primary_key=True)
        current_chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        bookmark_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
        has_bookmark: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        is_finished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        last_opened_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=_utcnow, nullable=False
        )

        document = relationship("Document")
