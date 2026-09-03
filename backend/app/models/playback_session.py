from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


if "PlaybackSession" not in globals():
    class PlaybackSession(Base):
        __tablename__ = "playback_sessions"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=True
        )
        document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
        chunk_id: Mapped[int] = mapped_column(ForeignKey("text_chunks.id"), index=True)
        current_chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
        engine_name: Mapped[str] = mapped_column(String(50))
        voice_option_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        playback_speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
        audio_path: Mapped[str] = mapped_column(String(1024))
