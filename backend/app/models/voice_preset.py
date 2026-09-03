from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


if "VoicePreset" not in globals():
    class VoicePreset(Base):
        __tablename__ = "voice_presets"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        owner_user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=True
        )
        name: Mapped[str] = mapped_column(String(255))
        engine: Mapped[str] = mapped_column(String(50))
        reference_path: Mapped[str] = mapped_column(String(1024))
        transcript: Mapped[str] = mapped_column(Text)
        source_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
        source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
        transcript_source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
        license_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
        provenance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
