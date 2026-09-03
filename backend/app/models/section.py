from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


if "Section" not in globals():
    class Section(Base):
        __tablename__ = "sections"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
        position: Mapped[int] = mapped_column(Integer)
        title: Mapped[str | None] = mapped_column(String(255), nullable=True)
        text: Mapped[str] = mapped_column(Text)

        document = relationship("Document")
        chunks = relationship(
            "TextChunk",
            back_populates="section",
            cascade="all, delete-orphan",
            order_by="TextChunk.position",
        )
