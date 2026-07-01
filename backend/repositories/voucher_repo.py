"""Voucher repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Voucher


async def create(
    db: AsyncSession,
    *,
    code: str,
    value_paise: int | None = None,
    value_minutes: int | None = None,
    status: str | None = None,
    batch_id: str = "",
    expires_at: str | None = None,
) -> Voucher:
    voucher = Voucher(
        code=code,
        value_paise=value_paise,
        value_minutes=value_minutes,
        status=status,
        batch_id=batch_id,
        expires_at=expires_at,
    )
    db.add(voucher)
    await db.flush()

    await db.refresh(voucher)
    return voucher


async def get_by_id(db: AsyncSession, voucher_id: str) -> Voucher | None:
    result = await db.execute(select(Voucher).where(Voucher.id == voucher_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Voucher]:
    result = await db.execute(select(Voucher))
    return result.scalars().all()


async def update(db: AsyncSession, voucher: Voucher) -> Voucher:
    db.add(voucher)
    await db.flush()
    await db.refresh(voucher)
    return voucher


async def delete_by_id(db: AsyncSession, voucher_id: str) -> bool:
    voucher = await get_by_id(db, voucher_id)
    if voucher is None:
        return False
    await db.delete(voucher)
    await db.flush()
    return True
