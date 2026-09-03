from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


if "Collection" not in globals():
    class Collection(Base):
        __tablename__ = "collections"
        __table_args__ = {"extend_existing": True}

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        owner_user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=True
        )
        name: Mapped[str] = mapped_column(String(255))
        description: Mapped[str | None] = mapped_column(Text, nullable=True)

        membership_rows = relationship(
            "CollectionDocument",
            cascade="all, delete-orphan",
            back_populates="collection",
        )


if "CollectionDocument" not in globals():
    class CollectionDocument(Base):
        __tablename__ = "collection_documents"
        __table_args__ = {"extend_existing": True}

        collection_id: Mapped[int] = mapped_column(
            ForeignKey("collections.id"), primary_key=True
        )
        document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), primary_key=True)

        collection = relationship("Collection", back_populates="membership_rows")
