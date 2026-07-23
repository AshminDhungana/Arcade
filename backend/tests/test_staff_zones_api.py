"""Tests for staff_zones API router."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.main import app
from backend.models._enums import PricingModel, StaffRole
from backend.models.staff import Staff
from backend.models.zone import Zone


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


@pytest_asyncio.fixture
async def setup_data(db: AsyncSession):
    admin = Staff(
        id="admin1",
        name="Admin",
        role=StaffRole.ADMIN,
        pin_hash="hash",
        is_active=True,
        token_version=0,
    )
    cashier = Staff(
        id="cashier1",
        name="Cashier",
        role=StaffRole.CASHIER,
        pin_hash="hash",
        is_active=True,
        token_version=0,
    )
    cashier2 = Staff(
        id="cashier2",
        name="Cashier2",
        role=StaffRole.CASHIER,
        pin_hash="hash",
        is_active=True,
        token_version=0,
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

    db.add_all([admin, cashier, cashier2, zone, zone2])
    await db.flush()
    return {
        "admin": admin,
        "cashier": cashier,
        "cashier2": cashier2,
        "zone": zone,
        "zone2": zone2,
    }


@pytest_asyncio.fixture
async def client_admin(db: AsyncSession, setup_data) -> AsyncGenerator[AsyncClient]:
    """Create test client with admin auth."""
    app.dependency_overrides[get_db] = lambda: db

    async def override_get_current_staff_admin(request: Request):
        return setup_data["admin"]

    app.dependency_overrides[get_current_staff] = override_get_current_staff_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_cashier(db: AsyncSession, setup_data) -> AsyncGenerator[AsyncClient]:
    """Create test client with cashier auth."""
    app.dependency_overrides[get_db] = lambda: db

    async def override_get_current_staff_cashier(request: Request):
        return setup_data["cashier"]

    app.dependency_overrides[get_current_staff] = override_get_current_staff_cashier

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_cashier2(db: AsyncSession, setup_data) -> AsyncGenerator[AsyncClient]:
    """Create test client with cashier2 auth."""
    app.dependency_overrides[get_db] = lambda: db

    async def override_get_current_staff_cashier2(request: Request):
        return setup_data["cashier2"]

    app.dependency_overrides[get_current_staff] = override_get_current_staff_cashier2

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def clients(db: AsyncSession, setup_data):
    """Create both admin and cashier clients that share the same DB session.
    Use this for tests that need to switch between clients.
    """
    app.dependency_overrides[get_db] = lambda: db

    async def override_admin(request: Request):
        return setup_data["admin"]

    async def override_cashier(request: Request):
        return setup_data["cashier"]

    transport = ASGITransport(app=app)
    admin_client = AsyncClient(transport=transport, base_url="http://test")
    cashier_client = AsyncClient(transport=transport, base_url="http://test")

    # We'll swap the override before each call
    async def make_admin(client):
        app.dependency_overrides[get_current_staff] = override_admin
        return client

    async def make_cashier(client):
        app.dependency_overrides[get_current_staff] = override_cashier
        return client

    yield {
        "admin": admin_client,
        "cashier": cashier_client,
        "make_admin": make_admin,
        "make_cashier": make_cashier,
    }

    await admin_client.aclose()
    await cashier_client.aclose()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assign_zone_success(client_admin: AsyncClient, setup_data):
    """POST /staff/{id}/zones assigns zone to cashier."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    resp = await client_admin.post(
        f"/api/staff/{cashier.id}/zones",
        json={"zone_id": zone.id},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["zone_id"] == zone.id
    assert data["zone_name"] == zone.name
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_assign_zone_duplicate_409(client_admin: AsyncClient, setup_data):
    """Duplicate assignment returns 409."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await client_admin.post(f"/api/staff/{cashier.id}/zones", json={"zone_id": zone.id})
    resp = await client_admin.post(
        f"/api/staff/{cashier.id}/zones", json={"zone_id": zone.id}
    )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_assign_zone_admin_only(client_cashier: AsyncClient, setup_data):
    """Cashier cannot assign zones (403)."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    resp = await client_cashier.post(
        f"/api/staff/{cashier.id}/zones",
        json={"zone_id": zone.id},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_bulk_assign_zones(client_admin: AsyncClient, setup_data):
    """POST /staff/{id}/zones/bulk assigns multiple zones."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]
    zone2 = setup_data["zone2"]

    resp = await client_admin.post(
        f"/api/staff/{cashier.id}/zones/bulk",
        json={"zone_ids": [zone.id, zone2.id]},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    zone_ids = {z["zone_id"] for z in data}
    assert zone_ids == {zone.id, zone2.id}


@pytest.mark.asyncio
async def test_list_staff_zones(client_admin: AsyncClient, setup_data):
    """GET /staff/{id}/zones lists assignments."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await client_admin.post(f"/api/staff/{cashier.id}/zones", json={"zone_id": zone.id})

    resp = await client_admin.get(f"/api/staff/{cashier.id}/zones")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["zone_id"] == zone.id


@pytest.mark.asyncio
async def test_revoke_zone(client_admin: AsyncClient, setup_data):
    """DELETE /staff/{id}/zones/{zone_id} revokes access."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    await client_admin.post(f"/api/staff/{cashier.id}/zones", json={"zone_id": zone.id})

    resp = await client_admin.delete(f"/api/staff/{cashier.id}/zones/{zone.id}")

    assert resp.status_code == 204

    # Verify revoked
    resp2 = await client_admin.get(f"/api/staff/{cashier.id}/zones")
    assert len(resp2.json()) == 0


@pytest.mark.asyncio
async def test_get_my_zones_admin(client_admin: AsyncClient, setup_data):
    """GET /staff/me/zones returns all zones for admin."""
    resp = await client_admin.get("/api/staff/me/zones")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2  # admin sees all zones


@pytest.mark.asyncio
async def test_get_my_zones_cashier(client_cashier: AsyncClient, setup_data):
    """GET /staff/me/zones returns only assigned zones for cashier."""
    # Cashier has no zones yet
    resp = await client_cashier.get("/api/staff/me/zones")

    assert resp.status_code == 200
    data = resp.json()
    assert data == []


@pytest.mark.asyncio
async def test_get_my_zones_cashier_with_zones(clients, setup_data):
    """Cashier sees only their assigned zones."""
    cashier = setup_data["cashier"]
    zone = setup_data["zone"]

    # Admin assigns only zone1
    admin_client = await clients["make_admin"](clients["admin"])
    await admin_client.post(f"/api/staff/{cashier.id}/zones", json={"zone_id": zone.id})

    # Cashier checks their zones
    cashier_client = await clients["make_cashier"](clients["cashier"])
    resp = await cashier_client.get("/api/staff/me/zones")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["zone_id"] == zone.id
