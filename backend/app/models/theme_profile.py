from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


if "ThemeProfile" not in globals():
    class ThemeProfile(Base):
        __tablename__ = "theme_profiles"
        __table_args__ = {"extend_existing": True}

        id: Mapped[str] = mapped_column(String(100), primary_key=True)
        owner_user_id: Mapped[int | None] = mapped_column(
            ForeignKey("users.id"), index=True, nullable=True
        )
        name: Mapped[str] = mapped_column(String(255), nullable=False)
        description: Mapped[str | None] = mapped_column(Text, nullable=True)
        source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
        source_label: Mapped[str] = mapped_column(String(255), nullable=False)
        source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
        is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
        sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
        family: Mapped[str] = mapped_column(String(64), nullable=False, default="house")
        preview_variant: Mapped[str] = mapped_column(
            String(64), nullable=False, default="standard"
        )
        background_asset_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
        background_overlay_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
        shelf_asset_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
        surface_texture_asset_path: Mapped[str | None] = mapped_column(
            String(255), nullable=True
        )
        supports_mix_and_match: Mapped[bool] = mapped_column(
            Boolean, nullable=False, default=True
        )
        tokens_json: Mapped[str] = mapped_column(Text, nullable=False)
