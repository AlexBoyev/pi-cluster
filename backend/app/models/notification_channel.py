from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # "webhook" (default, original type) or "email". Exactly one of
    # url/email_address is populated depending on channel_type - enforced in
    # the schema/service layer, not a DB constraint, to avoid rewriting the
    # column for pre-existing webhook rows.
    channel_type: Mapped[str] = mapped_column(String(16), nullable=False, default="webhook")
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
