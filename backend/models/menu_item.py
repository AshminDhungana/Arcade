"""MenuItem model — items available for POS ordering."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    price_paise: Mapped[int] = mapped_column(default=0)
    stock_quantity: Mapped[int | None]
    low_stock_threshold: Mapped[int | None]
    is_available: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
