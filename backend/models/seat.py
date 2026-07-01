"""Seat model — individual gaming stations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import SeatStatus
from backend.models._types import StrEnumColumn


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("zones.id"), nullable=False
    )
    mac_address: Mapped[str | None] = mapped_column(String(17))
    status: Mapped[SeatStatus] = mapped_column(
        StrEnumColumn(SeatStatus, 15), nullable=False, default=SeatStatus.AVAILABLE
    )
    plug_id: Mapped[str | None] = mapped_column(String(255))
    is_console: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
