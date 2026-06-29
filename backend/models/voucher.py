"""Voucher model — gift/time vouchers for members."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import VoucherStatus


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    code: Mapped[str] = mapped_column(
        String(12), unique=True, nullable=False, index=True
    )
    value_paise: Mapped[int | None]
    value_minutes: Mapped[int | None]
    status: Mapped[VoucherStatus] = mapped_column(
        String(10), nullable=False, default=VoucherStatus.UNUSED
    )
    redeemed_by_member_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("members.id")
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    batch_id: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
