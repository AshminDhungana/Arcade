"""GamingSession model — tracks a single play session on a seat.

Named `GamingSession` to avoid shadowing :class:`sqlalchemy.orm.Session`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import PaymentMethod, PricingModel, SessionStatus
from backend.models._types import StrEnumColumn


class GamingSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    seat_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("seats.id"), nullable=False, index=True
    )
    member_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("members.id"), index=True
    )
    shift_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("shifts.id"))
    status: Mapped[SessionStatus] = mapped_column(
        StrEnumColumn(SessionStatus, 10), nullable=False, default=SessionStatus.ACTIVE
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_paused_seconds: Mapped[int] = mapped_column(default=0)
    # --- Assigned-time limit (Epic 6.5.4) ---
    assigned_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    expiry_warned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_rate_paise: Mapped[int]
    locked_pricing_model: Mapped[PricingModel] = mapped_column(
        StrEnumColumn(PricingModel, 15), nullable=False
    )
    package_entitlement_id: Mapped[str | None] = mapped_column(String(32))
    promotion_id: Mapped[str | None] = mapped_column(String(32))
    discount_paise: Mapped[int] = mapped_column(default=0)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        StrEnumColumn(PaymentMethod, 10)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.expiry_warned is None:
            self.expiry_warned = False
