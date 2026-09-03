from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


if "Job" not in globals():
    class Job(Base):
        __tablename__ = "jobs"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=True
        )
        document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
        voice_preset_id: Mapped[str] = mapped_column(String(255))
        clone_engine_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        format: Mapped[str] = mapped_column(String(50))
        status: Mapped[str] = mapped_column(String(50), default="queued")
        split_chapters: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
        artifact_basename: Mapped[str] = mapped_column(
            String(255), default="export", nullable=False
        )
        progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        status_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
        artifact_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
        artifact_manifest: Mapped[str | None] = mapped_column(Text, nullable=True)
        failure_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
        heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

        document = relationship("Document")
