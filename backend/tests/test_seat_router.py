"""Integration tests for the Seat API router.

Uses :class:`fastapi.testclient.TestClient` with dependency overrides to
bypass JWT auth in favour of a mock staff object.
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.security import hash_pin
from backend.main import app
from backend.models._enums import PricingModel, StaffRole
from backend.models.staff import Staff
from backend.models.zone import Zone
from backend.repositories import staff_repo

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def admin_staff(db: AsyncSession) -> Staff:
    """Create a real admin staff record in the test DB."""
    return await staff_repo.create(
        db, name="Test Admin", pin_hash=hash_pin("1234"), role=StaffRole.ADMIN.value
    )


@pytest_asyncio.fixture
async def cashier_staff(db: AsyncSession) -> Staff:
    """Create a real cashier staff record in the test DB."""
    return await staff_repo.create(
        db, name="Test Cashier", pin_hash=hash_pin("1234"), role=StaffRole.CASHIER.value
    )


@pytest_asyncio.fixture
async def client(db: AsyncSession, admin_staff: Staff) -> AsyncGenerator[TestClient]:
    """Yield a TestClient that bypasses auth using real admin staff."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def cashier_client(
    db: AsyncSession, cashier_staff: Staff
) -> AsyncGenerator[TestClient]:
    """Yield a TestClient authenticated as a cashier (not admin)."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: cashier_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _clear_seats(db: AsyncSession) -> None:
    """Truncate seats so isolation-sensitive assertions aren't poisoned by rows
    left in the shared persistent test DB by other tests.

    ``foreign_keys`` is toggled off locally for the delete so we don't have to
    enumerate every FK-dependent table; the engine re-asserts it per connection.
    """
    await db.execute(text("PRAGMA foreign_keys=OFF"))
    await db.execute(text("DELETE FROM seats"))
    await db.execute(text("PRAGMA foreign_keys=ON"))
    await db.commit()


async def _ensure_zone(db: AsyncSession) -> None:
    """Ensure zone1 exists in test DB."""
    from sqlalchemy import select

    result = await db.execute(select(Zone).where(Zone.id == "zone1"))
    zone = result.scalar_one_or_none()
    if zone is None:
        zone = Zone(
            id="zone1",
            name="Test Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        db.add(zone)
        await db.commit()


def test_list_seats_empty(client: TestClient, db: AsyncSession) -> None:
    asyncio.run(_clear_seats(db))
    asyncio.run(_ensure_zone(db))
    resp = client.get("/api/seats")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_seats_returns_list(client: TestClient, db: AsyncSession) -> None:
    asyncio.run(_ensure_zone(db))
    resp = client.get("/api/seats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GET /api/seats/{seat_id}
# ---------------------------------------------------------------------------


def test_get_seat_not_found(client: TestClient, db: AsyncSession) -> None:
    asyncio.run(_ensure_zone(db))
    resp = client.get("/api/seats/non-existent-id")
    assert resp.status_code == 404
    assert "non-existent-id" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# PATCH /api/seats/{seat_id}/maintenance (admin only)
# ---------------------------------------------------------------------------


def test_set_maintenance_admin_only(
    cashier_client: TestClient, db: AsyncSession
) -> None:
    """Cashier role should be denied when calling set_maintenance."""
    asyncio.run(_ensure_zone(db))
    resp = cashier_client.patch("/api/seats/123/maintenance", json={"note": "test"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/seats/{seat_id}/maintenance (admin only)
# ---------------------------------------------------------------------------


def test_clear_maintenance_admin_only(
    cashier_client: TestClient, db: AsyncSession
) -> None:
    """Cashier role should be denied when calling clear_maintenance."""
    asyncio.run(_ensure_zone(db))
    resp = cashier_client.delete("/api/seats/123/maintenance")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Auth / role checks
# ---------------------------------------------------------------------------


def test_list_seats_requires_auth() -> None:
    """Accessing /api/seats without a valid token should be rejected."""
    # Ensure no auth override is active
    if get_current_staff in app.dependency_overrides:
        del app.dependency_overrides[get_current_staff]

    with TestClient(app) as c:
        resp = c.get("/api/seats")
    # Expect 401 because no Authorization header
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/seats/{seat_id}/wol (admin only)
# ---------------------------------------------------------------------------


def test_trigger_wol_admin_only(cashier_client: TestClient, db: AsyncSession) -> None:
    """Cashier role should be denied when calling trigger WoL."""
    asyncio.run(_ensure_zone(db))
    resp = cashier_client.post("/api/seats/123/wol")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/seats/{seat_id}/wol/override (admin only)
# ---------------------------------------------------------------------------


def test_wol_override_admin_only(cashier_client: TestClient, db: AsyncSession) -> None:
    """Cashier role should be denied when calling WoL override."""
    asyncio.run(_ensure_zone(db))
    resp = cashier_client.post("/api/seats/123/wol/override")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/seats (admin only)
# ---------------------------------------------------------------------------


def test_create_seat_admin_only(cashier_client: TestClient, db: AsyncSession) -> None:
    """Cashier role should be denied when creating a seat."""
    asyncio.run(_ensure_zone(db))
    resp = cashier_client.post(
        "/api/seats",
        json={"name": "PC-01", "zone_id": "zone1"},
    )
    assert resp.status_code == 403


def test_create_seat_success(client: TestClient, db: AsyncSession) -> None:
    """Admin can create a seat with valid zone."""
    asyncio.run(_ensure_zone(db))
    resp = client.post(
        "/api/seats",
        json={"name": "PC-01", "zone_id": "zone1", "mac_address": "aa:bb:cc:dd:ee:ff"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "PC-01"
    assert data["zone_id"] == "zone1"
    assert data["mac_address"] == "aa:bb:cc:dd:ee:ff"
    assert "id" in data


def test_create_seat_invalid_zone(client: TestClient, db: AsyncSession) -> None:
    """Creating a seat with non-existent zone returns 404."""
    asyncio.run(_ensure_zone(db))
    resp = client.post(
        "/api/seats",
        json={"name": "PC-02", "zone_id": "non-existent-zone"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/seats/{seat_id} (admin only)
# ---------------------------------------------------------------------------


def test_update_seat_admin_only(cashier_client: TestClient, db: AsyncSession) -> None:
    """Cashier role should be denied when updating a seat."""
    asyncio.run(_ensure_zone(db))
    resp = cashier_client.patch(
        "/api/seats/123",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 403


def test_update_seat_success(client: TestClient, db: AsyncSession) -> None:
    """Admin can update a seat."""
    asyncio.run(_ensure_zone(db))
    # First create a seat
    resp = client.post("/api/seats", json={"name": "PC-Original", "zone_id": "zone1"})
    assert resp.status_code == 201
    seat_id = resp.json()["id"]

    # Update the seat
    resp = client.patch(f"/api/seats/{seat_id}", json={"name": "PC-Updated"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "PC-Updated"


def test_update_seat_invalid_zone(client: TestClient, db: AsyncSession) -> None:
    """Updating a seat with non-existent zone returns 404."""
    asyncio.run(_ensure_zone(db))
    resp = client.post("/api/seats", json={"name": "PC-Original", "zone_id": "zone1"})
    assert resp.status_code == 201
    seat_id = resp.json()["id"]

    resp = client.patch(f"/api/seats/{seat_id}", json={"zone_id": "non-existent-zone"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/seats/{seat_id} (admin only)
# ---------------------------------------------------------------------------


def test_delete_seat_admin_only(cashier_client: TestClient, db: AsyncSession) -> None:
    """Cashier role should be denied when deleting a seat."""
    asyncio.run(_ensure_zone(db))
    resp = cashier_client.delete("/api/seats/123")
    assert resp.status_code == 403


def test_delete_seat_success(client: TestClient, db: AsyncSession) -> None:
    """Admin can delete a seat."""
    asyncio.run(_ensure_zone(db))
    resp = client.post("/api/seats", json={"name": "PC-ToDelete", "zone_id": "zone1"})
    assert resp.status_code == 201
    seat_id = resp.json()["id"]

    resp = client.delete(f"/api/seats/{seat_id}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = client.get(f"/api/seats/{seat_id}")
    assert resp.status_code == 404
