"""Tests for seat_repo."""

from __future__ import annotations

import pytest

from backend.repositories import seat_repo, zone_repo
from backend.core.database import AsyncSessionLocal
from backend.models import Seat
from backend.models._enums import PricingModel


@pytest.mark.asyncio
async def test_get_all_seat_ids():
    async with AsyncSessionLocal() as db:
        # Create a zone first (FK constraint)
        zone = await zone_repo.create(
            db,
            name="Test Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()

        # Create test seats
        seat1 = await seat_repo.create(db, name="Seat 1", zone_id=zone.id)
        seat2 = await seat_repo.create(db, name="Seat 2", zone_id=zone.id)
        await db.commit()

        # Call function
        ids = await seat_repo.get_all_seat_ids(db)

        assert seat1.id in ids
        assert seat2.id in ids
        assert len(ids) >= 2