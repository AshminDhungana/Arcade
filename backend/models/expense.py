"""Expense model — operational cost tracking."""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import ExpenseCategory


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    date: Mapped[_dt.date] = mapped_column(
        DateTime(timezone=True),
        default=lambda: _dt.datetime.now(_dt.UTC).date(),
        nullable=False,
    )
    category: Mapped[ExpenseCategory] = mapped_column(String(20), nullable=False)
    amount_paise: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(1000))
    logged_by_staff_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("staff.id"), nullable=False
    )
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: _dt.datetime.now(_dt.UTC),
        nullable=False,
    )
