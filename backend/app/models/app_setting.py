from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


if "AppSetting" not in globals():
    class AppSetting(Base):
        __tablename__ = "app_settings"
        __table_args__ = {"extend_existing": True}

        key: Mapped[str] = mapped_column(String(100), primary_key=True)
        value: Mapped[str | None] = mapped_column(Text, nullable=True)
