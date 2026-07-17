# backend/tests/test_session_repo.py
"""Unit tests for :mod:`backend.repositories.session_repo`."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import GamingSession, SessionStatus
from backend.models._enums import PricingModel
from backend.repositories import seat_repo, session_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on an in-memory SQLite DB."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def zone_and_seat(db: AsyncSession):
    """Create a zone and seat; return (zone, seat)."""
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()

    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    return zone, seat


async def test_create_with_shift_id_stores_it(db: AsyncSession) -> None:
    s = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id="shift-9",
    )
    assert s.shift_id == "shift-9"


async def test_create_without_shift_id_is_none(db: AsyncSession) -> None:
    s = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    assert s.shift_id is None


async def test_list_active_with_assigned_end(db: AsyncSession, zone_and_seat):
    """list_active_with_assigned_end returns ACTIVE/PAUSED sessions with non-null
    assigned_end_at.
    """
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    with_assigned = GamingSession(
        seat_id=seat.id,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model="PER_MINUTE",
        status=SessionStatus.ACTIVE,
        assigned_end_at=now + timedelta(minutes=10),
    )
    no_assigned = GamingSession(
        seat_id=seat.id,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model="PER_MINUTE",
        status=SessionStatus.ACTIVE,
    )
    db.add(with_assigned)
    db.add(no_assigned)
    await db.commit()
    await db.refresh(with_assigned)
    result = await session_repo.list_active_with_assigned_end(db)
    ids = {s.id for s in result}
    assert with_assigned.id in ids
    assert no_assigned.id not in ids


async def test_assigned_end_at_by_seat(db: AsyncSession, zone_and_seat):
    """assigned_end_at_by_seat maps seat_id -> assigned_end_at for active
    sessions with a limit.
    """
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    s = GamingSession(
        seat_id=seat.id,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model="PER_MINUTE",
        status=SessionStatus.ACTIVE,
        assigned_end_at=now + timedelta(minutes=30),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    mapping = await seat_repo.assigned_end_at_by_seat(db, [seat.id])
    assert mapping[seat.id] == s.assigned_end_at
