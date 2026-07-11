"""WalletTransaction — append-only ledger of member wallet changes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid4().hex
    )
    member_id: Mapped[str] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(32))  # TOPUP, PACKAGE_PURCHASE, ...
    amount_paise: Mapped[int] = mapped_column(Integer)  # signed
    balance_after_paise: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String(16))
    staff_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
