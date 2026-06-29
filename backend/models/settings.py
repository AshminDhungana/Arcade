"""AppSettings model — key-value store for feature flags and mutable config."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class AppSettings(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(4000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
