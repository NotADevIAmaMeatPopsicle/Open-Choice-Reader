from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


if "DocumentProfile" not in globals():
    class DocumentProfile(Base):
        __tablename__ = "document_profiles"
        __table_args__ = {"extend_existing": True}

        document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), primary_key=True)
        author: Mapped[str | None] = mapped_column(String(255), nullable=True)
        summary: Mapped[str | None] = mapped_column(Text, nullable=True)
        cover_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
        metadata_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
        metadata_source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        source_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
        source_provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        source_provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
        source_provider_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
        source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
        source_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
        import_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
        total_sections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        estimated_duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        imported_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=_utcnow, nullable=False
        )
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
        )

        document = relationship("Document")
