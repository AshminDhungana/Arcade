"""Unit tests for billing_service -- rate resolution and time charge calculation."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import backend.repositories.seat_repo as seat_repo
import backend.repositories.zone_repo as zone_repo
from backend.core.database import Base
from backend.models._enums import PricingModel
from backend.services.billing_service import (
    LockedRate,
    calculate_time_charge,
    resolve_rate,
)


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


# ------------------------------------------------------------------
# calculate_time_charge -- PER_MINUTE
# ------------------------------------------------------------------


def test_per_minute():
    locked = LockedRate(rate_paise=100, pricing_model=PricingModel.PER_MINUTE)
    assert calculate_time_charge(0, locked) == 0
    assert calculate_time_charge(30, locked) == 100  # ceil(0.5) = 1 minute
    assert calculate_time_charge(60, locked) == 100  # 1 minute
    assert calculate_time_charge(90, locked) == 200  # ceil(1.5) = 2 minutes
    assert calculate_time_charge(61, locked) == 200  # ceil(1.02) = 2 minutes


def test_per_minute_large_values():
    locked = LockedRate(rate_paise=50, pricing_model=PricingModel.PER_MINUTE)
    # 2 hours = 120 minutes at 50 paise/minute = 6000 paise
    assert calculate_time_charge(2 * 60 * 60, locked) == 120 * 50


# ------------------------------------------------------------------
# calculate_time_charge -- FLAT_HOURLY
# ------------------------------------------------------------------


def test_flat_hourly():
    locked = LockedRate(rate_paise=3000, pricing_model=PricingModel.FLAT_HOURLY)
    assert calculate_time_charge(0, locked) == 0
    assert calculate_time_charge(30, locked) == 3000  # ceil(0.0083) = 1 hour
    assert calculate_time_charge(3599, locked) == 3000  # ceil(0.9997) = 1 hour
    assert calculate_time_charge(3600, locked) == 3000  # exactly 1 hour
    assert calculate_time_charge(3601, locked) == 6000  # ceil(1.0002) = 2 hours


# ------------------------------------------------------------------
# calculate_time_charge -- TIME_BLOCK
# ------------------------------------------------------------------


def test_time_block():
    locked = LockedRate(
        rate_paise=1500, pricing_model=PricingModel.TIME_BLOCK, block_minutes=30
    )
    assert calculate_time_charge(0, locked) == 0
    assert calculate_time_charge(1, locked) == 1500  # ceil(1/1800)  = 1 block
    assert calculate_time_charge(29 * 60, locked) == 1500  # 29 min -> 1 block
    assert calculate_time_charge(30 * 60, locked) == 1500  # exactly 30 min
    assert calculate_time_charge(31 * 60, locked) == 3000  # 2 blocks


def test_time_block_missing_block_minutes():
    # If block_minutes is None, return 0 (no charge possible)
    locked = LockedRate(rate_paise=100, pricing_model=PricingModel.TIME_BLOCK)
    assert calculate_time_charge(300, locked) == 0


# ------------------------------------------------------------------
# resolve_rate
# ------------------------------------------------------------------


async def test_resolve_per_minute(db: AsyncSession) -> None:
    """resolve_rate returns PER_MINUTE locked rate from a zone."""
    z = await zone_repo.create(
        db,
        name="Standard",
        rate_per_minute_paise=50,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    s = await seat_repo.create(db, name="A1", zone_id=z.id)
    rate = await resolve_rate(db, s.id)
    assert rate == LockedRate(
        rate_paise=50,
        pricing_model=PricingModel.PER_MINUTE,
    )


async def test_resolve_flat_hourly(db: AsyncSession) -> None:
    """resolve_rate returns FLAT_HOURLY locked rate from a zone."""
    z = await zone_repo.create(
        db,
        name="VIP",
        rate_per_minute_paise=50,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.FLAT_HOURLY,
    )
    s = await seat_repo.create(db, name="A2", zone_id=z.id)
    rate = await resolve_rate(db, s.id)
    assert rate == LockedRate(
        rate_paise=5000,
        pricing_model=PricingModel.FLAT_HOURLY,
    )


async def test_resolve_time_block(db: AsyncSession) -> None:
    """resolve_rate returns TIME_BLOCK locked rate from a zone."""
    z = await zone_repo.create(
        db,
        name="Arcade",
        rate_per_minute_paise=200,
        rate_per_hour_paise=8000,
        pricing_model=PricingModel.TIME_BLOCK,
        block_minutes=30,
    )
    s = await seat_repo.create(db, name="A3", zone_id=z.id)
    rate = await resolve_rate(db, s.id)
    assert rate == LockedRate(
        rate_paise=200 * 30,
        pricing_model=PricingModel.TIME_BLOCK,
        block_minutes=30,
    )


async def test_resolve_missing_seat(db: AsyncSession) -> None:
    """resolve_rate raises 404 when seat does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await resolve_rate(db, "nonexistent-seat-id")
    assert exc_info.value.status_code == 404


async def test_resolve_missing_zone(db: AsyncSession) -> None:
    """resolve_rate raises 404 when seat's zone does not exist."""
    # Use unittest.mock to simulate zone missing
    from unittest.mock import patch

    z = await zone_repo.create(
        db,
        name="Temp",
        rate_per_minute_paise=50,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    s = await seat_repo.create(db, name="A4", zone_id=z.id)

    with patch(
        "backend.services.billing_service.zone_repo.get_by_id", return_value=None
    ):
        with pytest.raises(HTTPException) as exc_info:
            await resolve_rate(db, s.id)
        assert exc_info.value.status_code == 404


# ------------------------------------------------------------------
# Edge cases -- calculate_time_charge
# ------------------------------------------------------------------


def test_zero_and_negative_elapsed():
    """Non-positive elapsed seconds always returns 0."""
    locked = LockedRate(rate_paise=100, pricing_model=PricingModel.PER_MINUTE)
    assert calculate_time_charge(0, locked) == 0
    assert calculate_time_charge(-1, locked) == 0
    assert calculate_time_charge(-1000, locked) == 0


def test_very_large_elapsed():
    """Elapsed values up to 24 h work without overflow."""
    locked = LockedRate(rate_paise=100, pricing_model=PricingModel.PER_MINUTE)
    # 24 hours = 1440 minutes at 100 paise/minute = 144_000 paise
    assert calculate_time_charge(24 * 3600, locked) == 1440 * 100


async def test_zero_rate_per_minute(db: AsyncSession) -> None:
    """Zero paise rate yields zero charge."""
    z = await zone_repo.create(
        db,
        name="Free",
        rate_per_minute_paise=0,
        rate_per_hour_paise=0,
        pricing_model=PricingModel.PER_MINUTE,
    )
    s = await seat_repo.create(db, name="A5", zone_id=z.id)
    rate = await resolve_rate(db, s.id)
    assert rate == LockedRate(
        rate_paise=0,
        pricing_model=PricingModel.PER_MINUTE,
    )
    assert calculate_time_charge(3600, rate) == 0


# ------------------------------------------------------------------
# Integration -- full resolve + charge round-trip
# ------------------------------------------------------------------


async def test_resolve_and_charge_per_minute(db: AsyncSession) -> None:
    """Full round-trip: resolve a zone rate, then calculate charge."""
    z = await zone_repo.create(
        db,
        name="Standard",
        rate_per_minute_paise=120,
        rate_per_hour_paise=6000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    s = await seat_repo.create(db, name="B1", zone_id=z.id)
    locked = await resolve_rate(db, s.id)
    assert locked.pricing_model == PricingModel.PER_MINUTE
    assert locked.rate_paise == 120
    # 2.5 minutes = ceil(2.5) = 3 minutes -> 3 * 120 = 360 paise
    assert calculate_time_charge(150, locked) == 3 * 120


async def test_resolve_and_charge_flat_hourly(db: AsyncSession) -> None:
    """Full round-trip: resolve hourly zone rate, then calculate charge."""
    z = await zone_repo.create(
        db,
        name="VIP",
        rate_per_minute_paise=100,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.FLAT_HOURLY,
    )
    s = await seat_repo.create(db, name="B2", zone_id=z.id)
    locked = await resolve_rate(db, s.id)
    assert locked.pricing_model == PricingModel.FLAT_HOURLY
    assert locked.rate_paise == 5000
    # 90 minutes = ceil(1.5) = 2 hours -> 2 * 5000 = 10000 paise
    assert calculate_time_charge(90 * 60, locked) == 2 * 5000


async def test_resolve_and_charge_time_block(db: AsyncSession) -> None:
    """Full round-trip: resolve time-block zone rate, then calculate charge."""
    z = await zone_repo.create(
        db,
        name="Arcade",
        rate_per_minute_paise=50,
        rate_per_hour_paise=1500,
        pricing_model=PricingModel.TIME_BLOCK,
        block_minutes=45,
    )
    s = await seat_repo.create(db, name="B3", zone_id=z.id)
    locked = await resolve_rate(db, s.id)
    assert locked.pricing_model == PricingModel.TIME_BLOCK
    assert locked.block_minutes == 45
    assert locked.rate_paise == 50 * 45  # per-block rate
    # 100 minutes into 45-min blocks -> ceil(100/45) = ceil(2.22) = 3 blocks
    assert calculate_time_charge(100 * 60, locked) == 3 * 50 * 45
