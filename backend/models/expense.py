"""Expense model — operational cost tracking."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import ExpenseCategory


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    date: Mapped[date] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC).date(),
        nullable=False,
    )
    category: Mapped[ExpenseCategory] = mapped_column(String(20), nullable=False)
    amount_paise: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(1000))
    logged_by_staff_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("staff.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
