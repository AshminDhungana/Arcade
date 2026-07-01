"""Expense repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Expense


async def create(
    db: AsyncSession,
    *,
    date: str,
    category: str,
    amount_paise: int,
    note: str | None = None,
    logged_by_staff_id: str = "",
) -> Expense:
    expense = Expense(
        date=date,
        category=category,
        amount_paise=amount_paise,
        note=note,
        logged_by_staff_id=logged_by_staff_id,
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return expense


async def get_by_id(db: AsyncSession, expense_id: str) -> Expense | None:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Expense]:
    result = await db.execute(select(Expense))
    return result.scalars().all()


async def update(db: AsyncSession, expense: Expense) -> Expense:
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return expense


async def delete_by_id(db: AsyncSession, expense_id: str) -> bool:
    expense = await get_by_id(db, expense_id)
    if expense is None:
        return False
    await db.delete(expense)
    await db.flush()
    return True
