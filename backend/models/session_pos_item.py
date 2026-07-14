"""SessionPOSItem model — items ordered during a session."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class SessionPOSItem(Base):
    __tablename__ = "session_pos_items"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("sessions.id"), nullable=False, index=True
    )
    menu_item_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("menu_items.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price_paise: Mapped[int]
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
