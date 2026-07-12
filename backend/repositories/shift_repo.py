"""Shift repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Shift
from backend.models._enums import ShiftStatus


async def create(
    db: AsyncSession,
    *,
    opened_by_staff_id: str,
    opened_at: str,
    float_paise: int = 0,
    status: str | None = None,
) -> Shift:
    shift = Shift(
        opened_by_staff_id=opened_by_staff_id,
        opened_at=opened_at,
        float_paise=float_paise,
        status=status,
    )
    db.add(shift)
    await db.flush()
    await db.refresh(shift)
    return shift


async def get_by_id(db: AsyncSession, shift_id: str) -> Shift | None:
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    return result.scalar_one_or_none()


async def get_open_shift(db: AsyncSession) -> Shift | None:
    """Return the single OPEN shift, or ``None`` if none is open."""
    result = await db.execute(select(Shift).where(Shift.status == ShiftStatus.OPEN))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Shift]:
    result = await db.execute(select(Shift))
    return result.scalars().all()


async def update(db: AsyncSession, shift: Shift) -> Shift:
    db.add(shift)
    await db.flush()
    await db.refresh(shift)
    return shift


async def delete_by_id(db: AsyncSession, shift_id: str) -> bool:
    shift = await get_by_id(db, shift_id)
    if shift is None:
        return False
    await db.delete(shift)
    await db.flush()
    return True
