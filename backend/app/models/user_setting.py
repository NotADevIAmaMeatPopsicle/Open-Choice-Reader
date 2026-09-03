from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


if "UserSetting" not in globals():
    class UserSetting(Base):
        __tablename__ = "user_settings"
        __table_args__ = {"extend_existing": True}

        user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
        key: Mapped[str] = mapped_column(String(100), primary_key=True)
        value: Mapped[str | None] = mapped_column(Text, nullable=True)
