"""Tests for staff_zone_repo."""

from __future__ import annotations

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.models._enums import PricingModel, StaffRole
from backend.models.staff import Staff
from backend.models.staff_zone import StaffZone
from backend.models.zone import Zone
from backend.repositories import staff_zone_repo


def _make_test_sessionlocal():
    """Build a fresh async_sessionmaker bound to an in-memory aiosqlite engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Apply same pragmas as production to enforce FK constraints
    def _apply_pragmas(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA mmap_size = 134217728")
        cursor.execute("PRAGMA cache_size = -32000")
        cursor.execute("PRAGMA wal_autocheckpoint = 1000")
        cursor.close()

    event.listen(engine.sync_engine, "connect", _apply_pragmas)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    return engine, SessionLocal


async def _ensure_schema(engine) -> None:
    """Create all tables on the test engine."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _get_db_session():
    """Create a test database session."""
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    return engine, TestSessionLocal()


@pytest.fixture
async def db():
    """Create a test database session."""
    engine, session = await _get_db_session()
    try:
        yield session
    finally:
        await engine.dispose()


@pytest.fixture
async def setup_data(db: AsyncSession):
    """Create admin, cashier, zone for tests."""
    admin = Staff(
        id="admin1", name="Admin", role=StaffRole.ADMIN, pin_hash="hash", is_active=True
    )
    cashier = Staff(
        id="cashier1",
        name="Cashier",
        role=StaffRole.CASHIER,
        pin_hash="hash",
        is_active=True,
    )
    zone = Zone(
        id="zone1",
        name="Standard PC",
        rate_per_minute_paise=100,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    zone2 = Zone(
        id="zone2",
        name="VIP PC",
        rate_per_minute_paise=200,
        rate_per_hour_paise=10000,
        pricing_model=PricingModel.PER_MINUTE,
    )

    db.add_all([admin, cashier, zone, zone2])
    await db.flush()
    return {"admin": admin, "cashier": cashier, "zone": zone, "zone2": zone2}


@pytest.mark.asyncio
async def test_assign_zone(db: AsyncSession, setup_data):
    """assign_zone creates StaffZone record."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]
    admin = setup_data["admin"]

    assignment = await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
    )

    assert assignment.staff_id == cashier.id
    assert assignment.zone_id == zone.id
    assert assignment.granted_by == admin.id
    assert assignment.is_active is True


@pytest.mark.asyncio
async def test_revoke_zone(db: AsyncSession, setup_data):
    """revoke_zone soft-deletes (is_active=False)."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]
    admin = setup_data["admin"]

    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
    )

    ok = await staff_zone_repo.revoke_zone(db, staff_id=cashier.id, zone_id=zone.id)

    assert ok is True

    # Verify soft delete
    result = await db.execute(
        select(StaffZone).where(
            StaffZone.staff_id == cashier.id, StaffZone.zone_id == zone.id
        )
    )
    assignment = result.scalars().first()
    assert assignment is not None
    assert assignment.is_active is False


@pytest.mark.asyncio
async def test_revoke_nonexistent(db: AsyncSession, setup_data):
    """revoke_zone returns False for non-existent assignment."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    ok = await staff_zone_repo.revoke_zone(db, staff_id=cashier.id, zone_id=zone.id)

    assert ok is False


@pytest.mark.asyncio
async def test_list_zones_for_staff(db: AsyncSession, setup_data):
    """list_zones_for_staff returns active assignments only."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]
    zone2 = setup_data["zone2"]
    admin = setup_data["admin"]

    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
    )
    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone2.id, granted_by=admin.id
    )
    await staff_zone_repo.revoke_zone(
        db, staff_id=cashier.id, zone_id=zone.id
    )  # Deactivate zone1

    assignments = await staff_zone_repo.list_zones_for_staff(db, cashier.id)

    assert len(assignments) == 1
    assert assignments[0].zone_id == zone2.id
    assert assignments[0].is_active is True


@pytest.mark.asyncio
async def test_get_zone_ids_for_staff(db: AsyncSession, setup_data):
    """get_zone_ids_for_staff returns list of zone IDs."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]
    zone2 = setup_data["zone2"]
    admin = setup_data["admin"]

    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
    )
    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone2.id, granted_by=admin.id
    )

    zone_ids = await staff_zone_repo.get_zone_ids_for_staff(db, cashier.id)

    assert set(zone_ids) == {zone.id, zone2.id}


@pytest.mark.asyncio
async def test_get_zone_ids_for_staff_empty(db: AsyncSession, setup_data):
    """get_zone_ids_for_staff returns empty list for staff with no zones."""
    cashier = setup_data["cashier"]

    zone_ids = await staff_zone_repo.get_zone_ids_for_staff(db, cashier.id)

    assert zone_ids == []


@pytest.mark.asyncio
async def test_is_staff_assigned_to_zone(db: AsyncSession, setup_data):
    """is_staff_assigned_to_zone checks active assignment."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]
    admin = setup_data["admin"]

    assert (
        await staff_zone_repo.is_staff_assigned_to_zone(
            db, staff_id=cashier.id, zone_id=zone.id
        )
        is False
    )

    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
    )

    assert (
        await staff_zone_repo.is_staff_assigned_to_zone(
            db, staff_id=cashier.id, zone_id=zone.id
        )
        is True
    )

    await staff_zone_repo.revoke_zone(db, staff_id=cashier.id, zone_id=zone.id)

    assert (
        await staff_zone_repo.is_staff_assigned_to_zone(
            db, staff_id=cashier.id, zone_id=zone.id
        )
        is False
    )


@pytest.mark.asyncio
async def test_list_staff_for_zone(db: AsyncSession, setup_data):
    """list_staff_for_zone returns staff assigned to a zone."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]
    admin = setup_data["admin"]

    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
    )

    assignments = await staff_zone_repo.list_staff_for_zone(db, zone.id)

    assert len(assignments) == 1
    assert assignments[0].staff_id == cashier.id
