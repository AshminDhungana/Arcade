"""Tests for startup module."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.core.database import AsyncSessionLocal
from backend.core.startup import initialize_seat_statuses
from backend.models import Seat, SeatStatus
from backend.models._enums import PricingModel
from backend.repositories import seat_repo, zone_repo


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


@pytest.mark.asyncio
async def test_initialize_seat_statuses_preserves_maintenance():
    """C.11: a MAINTENANCE seat (with maintenance_since) survives restart."""
    async with AsyncSessionLocal() as db:
        zone = await zone_repo.create(
            db,
            name="Maint Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()

        maint_seat = await seat_repo.create(db, name="Maint Seat", zone_id=zone.id)
        maint_seat.status = SeatStatus.MAINTENANCE
        maint_seat.maintenance_since = datetime.now(UTC)
        await db.commit()

        other_seat = await seat_repo.create(db, name="Other Seat", zone_id=zone.id)
        other_seat.status = SeatStatus.AVAILABLE
        await db.commit()

        # Call function
        await initialize_seat_statuses()

        # Verify fresh session: MAINTENANCE survives, others reset to OFFLINE
        async with AsyncSessionLocal() as db2:
            refreshed = await db2.get(Seat, maint_seat.id)
            assert refreshed.status == SeatStatus.MAINTENANCE
            assert refreshed.maintenance_since is not None
            refreshed_other = await db2.get(Seat, other_seat.id)
            assert refreshed_other.status == SeatStatus.OFFLINE
