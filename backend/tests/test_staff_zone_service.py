"""Tests for staff_zone_service."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models._enums import AuditAction, PricingModel, StaffRole
from backend.models.staff import Staff
from backend.models.zone import Zone
from backend.services.staff_zone_service import StaffZoneService


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB."""
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


@pytest.fixture
async def setup_data(db: AsyncSession):
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
async def test_assign_zone_success(db: AsyncSession, setup_data):
    """assign_zone grants access and logs audit."""
    admin = setup_data["admin"]
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await StaffZoneService.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, admin=admin
    )

    # Verify assignment exists
    from backend.repositories import staff_zone_repo

    has_access = await staff_zone_repo.is_staff_assigned_to_zone(
        db, staff_id=cashier.id, zone_id=zone.id
    )
    assert has_access is True

    # Verify audit log
    from sqlalchemy import select

    from backend.models.audit_log import AuditLog

    result = await db.execute(
        select(AuditLog).where(AuditLog.action == AuditAction.STAFF_ZONE_ASSIGNED)
    )
    audit = result.scalars().first()
    assert audit is not None
    assert audit.entity_id == f"{cashier.id}:{zone.id}"
    assert audit.staff_id == admin.id


@pytest.mark.asyncio
async def test_assign_zone_duplicate_raises(db: AsyncSession, setup_data):
    """assign_zone raises 409 if already assigned."""
    admin = setup_data["admin"]
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await StaffZoneService.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, admin=admin
    )

    with pytest.raises(HTTPException) as exc:
        await StaffZoneService.assign_zone(
            db, staff_id=cashier.id, zone_id=zone.id, admin=admin
        )

    assert exc.value.status_code == 409
    assert "already has access" in exc.value.detail


@pytest.mark.asyncio
async def test_assign_zone_nonexistent_staff_raises(db: AsyncSession, setup_data):
    """assign_zone raises 404 for non-existent staff."""
    admin = setup_data["admin"]
    zone = setup_data["zone"]

    with pytest.raises(HTTPException) as exc:
        await StaffZoneService.assign_zone(
            db, staff_id="nonexistent", zone_id=zone.id, admin=admin
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_assign_zone_nonexistent_zone_raises(db: AsyncSession, setup_data):
    """assign_zone raises 404 for non-existent zone."""
    admin = setup_data["admin"]
    cashier = setup_data["cashier"]

    with pytest.raises(HTTPException) as exc:
        await StaffZoneService.assign_zone(
            db, staff_id=cashier.id, zone_id="nonexistent", admin=admin
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_revoke_zone_success(db: AsyncSession, setup_data):
    """revoke_zone removes access and logs audit."""
    admin = setup_data["admin"]
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await StaffZoneService.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, admin=admin
    )
    await StaffZoneService.revoke_zone(
        db, staff_id=cashier.id, zone_id=zone.id, admin=admin
    )

    # Verify assignment revoked
    from backend.repositories import staff_zone_repo

    has_access = await staff_zone_repo.is_staff_assigned_to_zone(
        db, staff_id=cashier.id, zone_id=zone.id
    )
    assert has_access is False

    # Verify audit log
    from sqlalchemy import select

    from backend.models.audit_log import AuditLog

    result = await db.execute(
        select(AuditLog).where(AuditLog.action == AuditAction.STAFF_ZONE_REVOKED)
    )
    audit = result.scalars().first()
    assert audit is not None
    assert audit.entity_id == f"{cashier.id}:{zone.id}"


@pytest.mark.asyncio
async def test_revoke_zone_not_found_raises(db: AsyncSession, setup_data):
    """revoke_zone raises 404 if assignment not found."""
    admin = setup_data["admin"]
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    with pytest.raises(HTTPException) as exc:
        await StaffZoneService.revoke_zone(
            db, staff_id=cashier.id, zone_id=zone.id, admin=admin
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_accessible_zones_admin(db: AsyncSession, setup_data):
    """get_accessible_zones returns all zones for admin."""
    admin = setup_data["admin"]
    zone = setup_data["zone"]
    zone2 = setup_data["zone2"]

    # Admin has no explicit assignments but should see all
    zones = await StaffZoneService.get_accessible_zones(db, admin)

    assert len(zones) == 2
    zone_ids = {z.id for z in zones}
    assert zone_ids == {zone.id, zone2.id}


@pytest.mark.asyncio
async def test_get_accessible_zones_cashier(db: AsyncSession, setup_data):
    """get_accessible_zones returns only assigned zones for cashier."""
    admin = setup_data["admin"]
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await StaffZoneService.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, admin=admin
    )
    # zone2 not assigned

    zones = await StaffZoneService.get_accessible_zones(db, cashier)

    assert len(zones) == 1
    assert zones[0].id == zone.id


@pytest.mark.asyncio
async def test_get_accessible_zones_cashier_no_zones(db: AsyncSession, setup_data):
    """get_accessible_zones returns empty list for cashier with no zones."""
    cashier = setup_data["cashier"]

    zones = await StaffZoneService.get_accessible_zones(db, cashier)

    assert zones == []


@pytest.mark.asyncio
async def test_list_assignments_for_staff(db: AsyncSession, setup_data):
    """list_assignments_for_staff returns detailed assignments."""
    admin = setup_data["admin"]
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await StaffZoneService.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, admin=admin
    )

    assignments = await StaffZoneService.list_assignments_for_staff(db, cashier.id)

    assert len(assignments) == 1
    a = assignments[0]
    assert a["zone_id"] == zone.id
    assert a["zone_name"] == zone.name
    assert a["granted_by"] == admin.name
    assert a["is_active"] is True
