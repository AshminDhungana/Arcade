"""Tests for startup module."""

from __future__ import annotations

import pytest

from backend.core.startup import initialize_seat_statuses
from backend.core.database import AsyncSessionLocal
from backend.models import Seat, SeatStatus
from backend.repositories import seat_repo, zone_repo
from backend.models._enums import PricingModel


@pytest.mark.asyncio
async def test_initialize_seat_statuses_sets_all_offline():
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

# Create test seats with various statuses
        seat1 = await seat_repo.create(db, name="Seat 1", zone_id=zone.id)
        seat2 = await seat_repo.create(db, name="Seat 2", zone_id=zone.id)
        seat1.status = SeatStatus.AVAILABLE
        seat2.status = SeatStatus.IN_USE
        await db.commit()

        # Call function
        await initialize_seat_statuses()

        # Verify all seats are OFFLINE (use fresh session to avoid caching)
        async with AsyncSessionLocal() as db2:
            for seat_id in [seat1.id, seat2.id]:
                refreshed = await db2.get(Seat, seat_id)
                assert refreshed.status == SeatStatus.OFFLINE