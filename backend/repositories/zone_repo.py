"""Zone repository - CRUD helpers for the Zone model."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models._enums import PricingModel
from backend.models.zone import Zone


async def create(
    db: AsyncSession,
    *,
    name: str,
    rate_per_minute_paise: int,
    rate_per_hour_paise: int,
    pricing_model: PricingModel,
    block_minutes: int | None = None,
) -> Zone:
    """Create a new Zone."""
    zone = Zone(
        name=name,
        rate_per_minute_paise=rate_per_minute_paise,
        rate_per_hour_paise=rate_per_hour_paise,
        pricing_model=pricing_model,
        block_minutes=block_minutes,
    )
    db.add(zone)
    await db.flush()
    return zone


async def get_by_id(db: AsyncSession, zone_id: str) -> Zone | None:
    """Fetch a zone by primary key."""
    result = await db.execute(select(Zone).where(Zone.id == zone_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Zone]:  # noqa: A001
    """Return all zones ordered by name."""
    result = await db.execute(select(Zone).order_by(Zone.name))
    return result.scalars().all()
