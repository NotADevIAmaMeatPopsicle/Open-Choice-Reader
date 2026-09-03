from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


if "TextChunk" not in globals():
    class TextChunk(Base):
        __tablename__ = "text_chunks"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), index=True)
        position: Mapped[int] = mapped_column(Integer)
        text: Mapped[str] = mapped_column(Text)

        section = relationship("Section", back_populates="chunks")
