"""ZoneService — business logic for zone management.

All public functions are ``async def`` and accept ``db: AsyncSession`` first.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models._enums import PricingModel
from backend.models.zone import Zone
from backend.repositories import zone_repo


class ZoneService:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        name: str,
        rate_per_minute_paise: int,
        rate_per_hour_paise: int,
        pricing_model: PricingModel,
        block_minutes: int | None = None,
    ) -> Zone:
        """Create a new zone.

        Raises HTTPException(409) if a zone with the same name already exists,
        enforcing the unique-zone-name invariant (migration
        l1a2b3c4d5e6_add_unique_zones_and_seat_zone).
        """
        existing = await zone_repo.get_by_name(db, name)
        if existing is not None:
            raise HTTPException(status_code=409, detail=f"Zone '{name}' already exists")
        return await zone_repo.create(
            db,
            name=name,
            rate_per_minute_paise=rate_per_minute_paise,
            rate_per_hour_paise=rate_per_hour_paise,
            pricing_model=pricing_model,
            block_minutes=block_minutes,
        )

    @staticmethod
    async def get_by_id(db: AsyncSession, zone_id: str) -> Zone | None:
        """Fetch a zone by ID."""
        return await zone_repo.get_by_id(db, zone_id)

    @staticmethod
    async def list(db: AsyncSession) -> Sequence[Zone]:
        """Return all zones ordered by name."""
        return await zone_repo.list(db)

    @staticmethod
    async def update(db: AsyncSession, zone: Zone) -> Zone:
        """Update a zone.

        Raises HTTPException(409) if the new name collides with another zone.
        """
        clash = await zone_repo.get_by_name(db, zone.name)
        if clash is not None and clash.id != zone.id:
            raise HTTPException(
                status_code=409, detail=f"Zone '{zone.name}' already exists"
            )
        return await zone_repo.update(db, zone)

    @staticmethod
    async def delete(db: AsyncSession, zone_id: str) -> bool:
        """Delete a zone by ID.

        Returns True if deleted, False if not found.
        """
        return await zone_repo.delete_by_id(db, zone_id)
