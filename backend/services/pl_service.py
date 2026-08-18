"""P&L Service — read-only profit & loss aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Invoice
from backend.models._enums import ExpenseCategory
from backend.repositories import expense_repo


@dataclass(frozen=True)
class PLSummary:
    period_start: date
    period_end: date
    # Revenue
    session_revenue_paise: int
    pos_revenue_paise: int
    total_revenue_paise: int
    # Expenses
    expenses_by_category: dict[ExpenseCategory, int]
    total_expenses_paise: int
    # Profit
    gross_profit_paise: int
    net_profit_paise: int


async def _revenue_in_range(
    db: AsyncSession, start: date, end: date
) -> tuple[int, int, int]:
    """Returns (session_rev, pos_rev, total_rev) for invoices in [start, end]."""
    # end is inclusive, so use < end + 1 day
    from datetime import timedelta

    end_exclusive = end + timedelta(days=1)

    stmt = select(
        func.coalesce(func.sum(Invoice.time_charge_paise), 0),
        func.coalesce(func.sum(Invoice.pos_total_paise), 0),
        func.coalesce(func.sum(Invoice.total_paise), 0),
    ).where(Invoice.created_at >= start, Invoice.created_at < end_exclusive)
    session_rev, pos_rev, total_rev = (await db.execute(stmt)).one()
    return int(session_rev or 0), int(pos_rev or 0), int(total_rev or 0)


async def _expenses_in_range(
    db: AsyncSession, start: date, end: date
) -> tuple[dict[ExpenseCategory, int], int]:
    """Returns (expenses_by_category, total_expenses) for expenses in [start, end]."""
    expenses = await expense_repo.list(db)
    # Filter in Python (small dataset); could push to SQL if needed
    # Note: Expense.date is DateTime at runtime, but typed as date in model
    filtered = [
        e
        for e in expenses
        if start <= e.date.date() <= end  # type: ignore[attr-defined]
    ]

    by_cat: dict[ExpenseCategory, int] = {}
    total = 0
    for e in filtered:
        cat = e.category
        by_cat[cat] = by_cat.get(cat, 0) + e.amount_paise
        total += e.amount_paise
    return by_cat, total


async def get_pl_summary(db: AsyncSession, start: date, end: date) -> PLSummary:
    session_rev, pos_rev, total_rev = await _revenue_in_range(db, start, end)
    expenses_by_cat, total_exp = await _expenses_in_range(db, start, end)

    gross = total_rev  # no COGS tracking yet
    net = gross - total_exp

    return PLSummary(
        period_start=start,
        period_end=end,
        session_revenue_paise=session_rev,
        pos_revenue_paise=pos_rev,
        total_revenue_paise=total_rev,
        expenses_by_category=expenses_by_cat,
        total_expenses_paise=total_exp,
        gross_profit_paise=gross,
        net_profit_paise=net,
    )


async def get_monthly_pl(db: AsyncSession, year: int, month: int) -> PLSummary:
    from calendar import monthrange

    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return await get_pl_summary(db, start, end)
