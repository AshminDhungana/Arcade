"""Verify the reservation reminder job flips due seats and is flag-gated."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.scheduler import init_scheduler
from backend.models import SeatStatus
from backend.repositories import reservation_repo, seat_repo
from backend.services.reservation_service import mark_due_reservations_reserved


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def seat(db: AsyncSession) -> str:
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    created = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    return created.id


async def test_job_flips_due_seat_and_broadcasts(db, seat) -> None:
    await reservation_repo.create(
        db,
        seat_id=seat,
        customer_name="Eve",
        reserved_from=datetime.now(UTC) + timedelta(minutes=1),
        reserved_until=datetime.now(UTC) + timedelta(minutes=20),
        created_by_staff_id="staff-1",
    )
    with patch(
        "backend.core.ws_manager.manager.broadcast_to_dashboards", new=AsyncMock()
    ):
        updated = await mark_due_reservations_reserved(db)
    assert seat in updated
    refreshed = await seat_repo.get_by_id(db, seat)
    assert refreshed.status == SeatStatus.RESERVED


async def test_job_skips_non_available_seat(db, seat) -> None:
    seat_obj = await seat_repo.get_by_id(db, seat)
    seat_obj.status = SeatStatus.IN_USE  # type: ignore[assignment]
    await seat_repo.update(db, seat_obj)
    await reservation_repo.create(
        db,
        seat_id=seat,
        customer_name="Frank",
        reserved_from=datetime.now(UTC) + timedelta(minutes=1),
        reserved_until=datetime.now(UTC) + timedelta(minutes=20),
        created_by_staff_id="staff-1",
    )
    with patch(
        "backend.core.ws_manager.manager.broadcast_to_dashboards", new=AsyncMock()
    ):
        updated = await mark_due_reservations_reserved(db)
    assert updated == []
    assert (await seat_repo.get_by_id(db, seat)).status == SeatStatus.IN_USE


@pytest.mark.asyncio
async def test_scheduler_registers_reservation_job() -> None:
    scheduler = init_scheduler()
    job = scheduler.get_job("reservation_reminder")
    assert job is not None
    assert job.trigger.interval == timedelta(minutes=1)
    scheduler.shutdown(wait=False)
