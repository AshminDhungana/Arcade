"""Unit tests for ensure_default_staff and ensure_default_zone_and_seats
(idempotent default-account/zone/seat seed)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import Settings
from backend.core.database import Base
from backend.core.security import hash_pin, verify_pin
from backend.models._enums import PricingModel, SeatStatus, StaffRole
from backend.repositories import seat_repo, staff_repo, zone_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


def _settings() -> Settings:
    return Settings(
        admin_staff_id="admin",
        admin_pin_hash=hash_pin("admin"),
        cashier_staff_id="cashier",
        cashier_pin_hash=hash_pin("cashier"),
    )


def _settings_with_secrets(seat_count: int = 3) -> Settings:
    s = _settings()
    s.agent_secrets = {f"seat_{i+1}": f"secret-{i+1}" for i in range(seat_count)}
    return s


async def test_seeds_admin_and_cashier_with_explicit_ids(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    await ensure_default_staff(db, settings=_settings())
    await db.commit()

    admin = await staff_repo.get_by_id(db, "admin")
    cashier = await staff_repo.get_by_id(db, "cashier")
    assert admin is not None
    assert cashier is not None
    assert admin.role == StaffRole.ADMIN
    assert cashier.role == StaffRole.CASHIER
    assert admin.is_active and cashier.is_active
    assert verify_pin("admin", admin.pin_hash)
    assert verify_pin("cashier", cashier.pin_hash)


async def test_is_idempotent_on_second_call(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    await ensure_default_staff(db, settings=_settings())
    await db.commit()
    # First call creates rows; grab the admin id.
    admin_before = await staff_repo.get_by_id(db, "admin")
    # Second call must NOT create duplicates or error.
    await ensure_default_staff(db, settings=_settings())

    all_staff = await staff_repo.list(db)
    assert len(all_staff) == 2
    admin_after = await staff_repo.get_by_id(db, "admin")
    # Same row, not a new one (id is the fixed "admin").
    assert admin_after.id == admin_before.id == "admin"


async def test_does_not_seed_when_table_non_empty(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    # Pre-existing staff (e.g. dev seed or a previously
    # deleted/recreated admin).
    await staff_repo.create(
        db, name="Existing", role=StaffRole.ADMIN, pin_hash=hash_pin("0000")
    )
    await db.commit()

    await ensure_default_staff(db, settings=_settings())

    all_staff = await staff_repo.list(db)
    # Only the pre-existing row; default "admin" is NOT force-created.
    assert len(all_staff) == 1
    assert await staff_repo.get_by_id(db, "admin") is None


async def test_creates_default_zone_and_seats_from_config(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_zone_and_seats

    settings = _settings_with_secrets(3)
    await ensure_default_zone_and_seats(db, settings=settings)
    await db.commit()

    # One zone created
    zones = await zone_repo.list(db)
    assert len(zones) == 1
    zone = zones[0]
    assert zone.name == "Standard PC"
    assert zone.pricing_model == PricingModel.PER_MINUTE
    assert zone.rate_per_minute_paise == 200
    assert zone.rate_per_hour_paise == 12000

    # Three seats created with matching IDs and secrets
    seats = await seat_repo.list(db)
    assert len(seats) == 3
    for i, seat in enumerate(seats, 1):
        assert seat.id == f"seat_{i}"
        assert seat.name == f"PC {i}"
        assert seat.zone_id == zone.id
        assert seat.status == SeatStatus.OFFLINE
        assert seat.agent_secret == f"secret-{i}"


async def test_is_idempotent_zone_and_seats(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_zone_and_seats

    settings = _settings_with_secrets(2)
    await ensure_default_zone_and_seats(db, settings=settings)
    await db.commit()

    zone_before = (await zone_repo.list(db))[0]
    seats_before = await seat_repo.list(db)

    # Second call must NOT create duplicates
    await ensure_default_zone_and_seats(db, settings=settings)
    await db.commit()

    zones = await zone_repo.list(db)
    seats = await seat_repo.list(db)
    assert len(zones) == 1
    assert zones[0].id == zone_before.id
    assert len(seats) == len(seats_before)


async def test_does_not_seed_when_seats_exist(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_zone_and_seats

    # Pre-existing seat
    zone = await zone_repo.create(
        db, name="Existing Zone", rate_per_minute_paise=100, rate_per_hour_paise=6000,
        pricing_model=PricingModel.PER_MINUTE
    )
    await seat_repo.create(db, name="Existing Seat", zone_id=zone.id)
    await db.commit()

    settings = _settings_with_secrets(3)
    await ensure_default_zone_and_seats(db, settings=settings)

    zones = await zone_repo.list(db)
    seats = await seat_repo.list(db)
    # Only pre-existing zone/seat; defaults NOT force-created
    assert len(zones) == 1
    assert zones[0].name == "Existing Zone"
    assert len(seats) == 1
    assert seats[0].name == "Existing Seat"


async def test_uses_existing_zone_if_present(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_zone_and_seats

    # Pre-existing zone (but no seats)
    zone = await zone_repo.create(
        db,
        name="Pre-existing Zone",
        rate_per_minute_paise=300,
        rate_per_hour_paise=18000,
        pricing_model=PricingModel.FLAT_HOURLY,
    )
    await db.commit()

    settings = _settings_with_secrets(2)
    await ensure_default_zone_and_seats(db, settings=settings)
    await db.commit()

    zones = await zone_repo.list(db)
    seats = await seat_repo.list(db)
    assert len(zones) == 1
    assert zones[0].id == zone.id  # Reuses existing zone
    assert len(seats) == 2
    assert all(s.zone_id == zone.id for s in seats)
