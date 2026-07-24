"""Tests for StaffZone model."""

from __future__ import annotations

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


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
    from backend.core.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_staff_zone_model_creation():
    """StaffZone can be created with all required fields."""
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    try:
        async with TestSessionLocal() as db:
            from backend.models._enums import PricingModel, StaffRole
            from backend.models.staff import Staff
            from backend.models.staff_zone import StaffZone
            from backend.models.zone import Zone

            admin = Staff(
                id="admin1",
                name="Admin",
                role=StaffRole.ADMIN,
                pin_hash="hash",
                is_active=True,
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

            db.add_all([admin, cashier, zone])
            await db.flush()

            assignment = StaffZone(
                staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
            )
            db.add(assignment)
            await db.flush()

            assert assignment.staff_id == cashier.id
            assert assignment.zone_id == zone.id
            assert assignment.granted_by == admin.id
            assert assignment.is_active is True
            assert assignment.granted_at is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_staff_zone_composite_pk():
    """StaffZone enforces unique (staff_id, zone_id) pair."""
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    try:
        async with TestSessionLocal() as db:
            from backend.models._enums import PricingModel, StaffRole
            from backend.models.staff import Staff
            from backend.models.staff_zone import StaffZone
            from backend.models.zone import Zone

            admin = Staff(
                id="admin1",
                name="Admin",
                role=StaffRole.ADMIN,
                pin_hash="hash",
                is_active=True,
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

            db.add_all([admin, cashier, zone])
            await db.flush()

            assign1 = StaffZone(
                staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
            )
            db.add(assign1)
            await db.flush()

            assign2 = StaffZone(
                staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
            )
            db.add(assign2)

            with pytest.raises(IntegrityError):  # IntegrityError on duplicate PK
                await db.flush()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_staff_zone_cascade_delete_staff():
    """Deleting staff cascades-deletes their zone assignments."""
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    try:
        async with TestSessionLocal() as db:
            from backend.models._enums import PricingModel, StaffRole
            from backend.models.staff import Staff
            from backend.models.staff_zone import StaffZone
            from backend.models.zone import Zone

            admin = Staff(
                id="admin1",
                name="Admin",
                role=StaffRole.ADMIN,
                pin_hash="hash",
                is_active=True,
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

            db.add_all([admin, cashier, zone])
            await db.flush()

            assign = StaffZone(
                staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
            )
            db.add(assign)
            await db.flush()

            await db.delete(cashier)
            await db.flush()

            result = await db.get(StaffZone, (cashier.id, zone.id))
            assert result is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_staff_zone_cascade_delete_zone():
    """Deleting zone cascades-deletes assignments to it."""
    engine, TestSessionLocal = _make_test_sessionlocal()
    await _ensure_schema(engine)
    try:
        async with TestSessionLocal() as db:
            from backend.models._enums import PricingModel, StaffRole
            from backend.models.staff import Staff
            from backend.models.staff_zone import StaffZone
            from backend.models.zone import Zone

            admin = Staff(
                id="admin1",
                name="Admin",
                role=StaffRole.ADMIN,
                pin_hash="hash",
                is_active=True,
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

            db.add_all([admin, cashier, zone])
            await db.flush()

            assign = StaffZone(
                staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
            )
            db.add(assign)
            await db.flush()

            await db.delete(zone)
            await db.flush()

            # Expire the session to clear identity map, then check raw DB
            db.expunge_all()
            result = await db.execute(
                select(StaffZone).where(
                    StaffZone.staff_id == cashier.id, StaffZone.zone_id == zone.id
                )
            )
            assert result.scalars().first() is None
    finally:
        await engine.dispose()
