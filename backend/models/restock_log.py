"""RestockLog model — audit trail for inventory restock events."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class RestockLog(Base):
    __tablename__ = "restock_logs"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    menu_item_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("menu_items.id"), nullable=False
    )
    quantity_added: Mapped[int] = mapped_column(Integer, nullable=False)
    logged_by_staff_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("staff.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
