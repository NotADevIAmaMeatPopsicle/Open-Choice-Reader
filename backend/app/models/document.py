from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


if "Document" not in globals():
    class Document(Base):
        __tablename__ = "documents"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        owner_user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=True
        )
        title: Mapped[str] = mapped_column(String(255))
        format: Mapped[str] = mapped_column(String(50))
        status: Mapped[str] = mapped_column(String(50))
        source_path: Mapped[str] = mapped_column(String(1024))
        origin_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
