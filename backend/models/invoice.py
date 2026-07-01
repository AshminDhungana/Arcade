"""Invoice model — generated at session checkout."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import PaymentMethod
from backend.models._types import StrEnumColumn


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("sessions.id"), nullable=False
    )
    member_id: Mapped[str | None] = mapped_column(String(32))
    shift_id: Mapped[str | None] = mapped_column(String(32))
    time_charge_paise: Mapped[int] = mapped_column(default=0)
    package_credit_used_paise: Mapped[int] = mapped_column(default=0)
    discount_paise: Mapped[int] = mapped_column(default=0)
    pos_total_paise: Mapped[int] = mapped_column(default=0)
    total_paise: Mapped[int] = mapped_column(default=0)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        StrEnumColumn(PaymentMethod, 10), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
