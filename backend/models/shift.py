"""Shift model — cash drawer / staff shift tracking."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import ShiftStatus
from backend.models._types import StrEnumColumn


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    opened_by_staff_id: Mapped[str] = mapped_column(String(32), ForeignKey("staff.id"))
    closed_by_staff_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("staff.id")
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    float_paise: Mapped[int] = mapped_column(default=0)
    counted_paise: Mapped[int | None]
    status: Mapped[ShiftStatus] = mapped_column(
        StrEnumColumn(ShiftStatus, 10), nullable=False, default=ShiftStatus.OPEN
    )
