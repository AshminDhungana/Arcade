"""Promotion repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Promotion


async def create(
    db: AsyncSession,
    *,
    name: str,
    type: str,
    discount_type: str,
    discount_value: int | None = None,
    active_days: str | None = None,
    active_from_hour: int | None = None,
    active_to_hour: int | None = None,
    min_group_size: int | None = None,
    zone_restriction_id: str | None = None,
    is_active: bool = True,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> Promotion:
    promo = Promotion(  # noqa: A003
        name=name,
        type=type,
        discount_type=discount_type,
        discount_value=discount_value,
        active_days=active_days,
        active_from_hour=active_from_hour,
        active_to_hour=active_to_hour,
        min_group_size=min_group_size,
        zone_restriction_id=zone_restriction_id,
        is_active=is_active,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    db.add(promo)
    await db.flush()
    await db.refresh(promo)
    return promo


async def get_by_id(db: AsyncSession, promotion_id: str) -> Promotion | None:
    result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Promotion]:
    result = await db.execute(select(Promotion))
    return result.scalars().all()


async def update(db: AsyncSession, promotion: Promotion) -> Promotion:
    db.add(promotion)
    await db.flush()
    await db.refresh(promotion)
    return promotion


async def delete_by_id(db: AsyncSession, promotion_id: str) -> bool:
    promotion = await get_by_id(db, promotion_id)
    if promotion is None:
        return False
    await db.delete(promotion)
    await db.flush()
    return True
