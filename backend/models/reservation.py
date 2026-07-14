"""Reservation model — pre-booked seat slots."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import ReservationStatus
from backend.models._types import StrEnumColumn


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    seat_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("seats.id"), nullable=False
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    member_id: Mapped[str | None] = mapped_column(String(32))
    reserved_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    group_reservation_id: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[ReservationStatus] = mapped_column(
        StrEnumColumn(ReservationStatus, 10),
        nullable=False,
        default=ReservationStatus.PENDING,
    )
    created_by_staff_id: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
