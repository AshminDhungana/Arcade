"""Staff repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Staff


async def create(
    db: AsyncSession,
    *,
    name: str,
    role: str,
    pin_hash: str,
    is_active: bool = True,
) -> Staff:
    staff = Staff(
        name=name,
        role=role,
        pin_hash=pin_hash,
        is_active=is_active,
    )
    db.add(staff)
    await db.flush()
    await db.refresh(staff)
    return staff


async def get_by_id(db: AsyncSession, staff_id: str) -> Staff | None:
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Staff]:
    result = await db.execute(select(Staff))
    return result.scalars().all()


async def update(db: AsyncSession, staff: Staff) -> Staff:
    db.add(staff)
    await db.flush()
    await db.refresh(staff)
    return staff


async def delete_by_id(db: AsyncSession, staff_id: str) -> bool:
    staff = await get_by_id(db, staff_id)
    if staff is None:
        return False
    await db.delete(staff)
    await db.flush()
    return True
