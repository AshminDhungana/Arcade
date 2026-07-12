"""Unit tests for the reservation repository time-window queries."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import ReservationStatus
from backend.repositories import reservation_repo, seat_repo
from backend.repositories.reservation_repo import (
    find_conflicting,
    find_due,
)


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
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    created = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    return created.id


def _make(
    db, seat_id, start_offset_min, end_offset_min, status=ReservationStatus.PENDING
):
    start = datetime.now(UTC) + timedelta(minutes=start_offset_min)
    end = (
        datetime.now(UTC) + timedelta(minutes=end_offset_min)
        if end_offset_min is not None
        else None
    )
    return reservation_repo.create(
        db,
        seat_id=seat_id,
        customer_name="C",
        reserved_from=start,
        reserved_until=end,
        created_by_staff_id="staff-1",
        status=status,
    )


async def test_create_stores_datetime_and_notes(db, seat) -> None:
    r = await _make(db, seat, 10, 30)
    assert isinstance(r.reserved_from, datetime)
    assert r.status == ReservationStatus.PENDING


async def test_find_conflicting_overlap(db, seat) -> None:
    await _make(db, seat, 10, 30)  # existing [10,30)
    conflicts = await find_conflicting(
        db,
        seat_id=seat,
        reserved_from=datetime.now(UTC) + timedelta(minutes=20),
        reserved_until=datetime.now(UTC) + timedelta(minutes=40),
    )
    assert len(conflicts) == 1


async def test_find_conflicting_back_to_back_no_overlap(db, seat) -> None:
    await _make(db, seat, 10, 30)  # existing ends at 30
    conflicts = await find_conflicting(
        db,
        seat_id=seat,
        reserved_from=datetime.now(UTC) + timedelta(minutes=30),
        reserved_until=datetime.now(UTC) + timedelta(minutes=50),
    )
    assert conflicts == ()


async def test_find_conflicting_open_ended_new(db, seat) -> None:
    await _make(db, seat, 10, 30)
    conflicts = await find_conflicting(
        db,
        seat_id=seat,
        reserved_from=datetime.now(UTC) + timedelta(minutes=5),
        reserved_until=None,
    )
    assert len(conflicts) == 1


async def test_find_conflicting_excludes_cancelled(db, seat) -> None:
    await _make(db, seat, 10, 30, status=ReservationStatus.CANCELLED)
    conflicts = await find_conflicting(
        db,
        seat_id=seat,
        reserved_from=datetime.now(UTC) + timedelta(minutes=20),
        reserved_until=datetime.now(UTC) + timedelta(minutes=40),
    )
    assert conflicts == ()


async def test_find_due_within_window(db, seat) -> None:
    due = await _make(db, seat, 1, 5)  # starts in 1 min
    await _make(db, seat, 60, 90)  # starts in 60 min (outside window)
    found = await find_due(
        db,
        window_start=datetime.now(UTC),
        window_end=datetime.now(UTC) + timedelta(minutes=2),
    )
    assert [r.id for r in found] == [due.id]
