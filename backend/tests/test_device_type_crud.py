"""Integration tests for Device Types CRUD (admin-gated)."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.security import hash_pin
from backend.main import app
from backend.models._enums import StaffRole
from backend.models.staff import Staff
from backend.repositories import staff_repo


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
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
    return await staff_repo.create(
        db, name="Admin", pin_hash=hash_pin("1234"), role=StaffRole.ADMIN.value
    )


@pytest_asyncio.fixture
async def cashier_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db, name="Cashier", pin_hash=hash_pin("1234"), role=StaffRole.CASHIER.value
    )


@pytest_asyncio.fixture
async def client(db: AsyncSession, admin_staff: Staff) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def cashier_client(
    db: AsyncSession, cashier_staff: Staff
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: cashier_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


class TestCreateAndList:
    async def test_create_and_list(self, client: AsyncClient) -> None:
        # Create device type
        resp = await client.post(
            "/api/device-types",
            json={"name": "PC", "description": "Gaming PC"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "PC"
        assert data["description"] == "Gaming PC"
        device_type_id = data["id"]

        # List device types
        resp = await client.get("/api/device-types")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(z["id"] == device_type_id for z in data)


class TestGetAndUpdate:
    async def test_get_and_update(self, client: AsyncClient) -> None:
        # Create device type
        resp = await client.post(
            "/api/device-types",
            json={"name": "Console", "description": "Game Console"},
        )
        assert resp.status_code == 201
        device_type_id = resp.json()["id"]

        # Get device type
        resp = await client.get(f"/api/device-types/{device_type_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Console"
        assert data["description"] == "Game Console"

        # Update device type (PATCH-style: only description)
        resp = await client.put(
            f"/api/device-types/{device_type_id}",
            json={"description": "Gaming PC"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Gaming PC"
        # Unchanged fields
        assert data["name"] == "Console"


class TestDelete:
    async def test_delete(self, client: AsyncClient) -> None:
        # Create device type
        resp = await client.post(
            "/api/device-types",
            json={"name": "VR Headset", "description": "VR Device"},
        )
        assert resp.status_code == 201
        device_type_id = resp.json()["id"]

        # Delete device type
        resp = await client.delete(f"/api/device-types/{device_type_id}")
        assert resp.status_code == 204

        # Verify 404 on GET
        resp = await client.get(f"/api/device-types/{device_type_id}")
        assert resp.status_code == 404


class TestAuthZoning:
    async def test_cashier_rejected(self, cashier_client: AsyncClient) -> None:
        resp = await cashier_client.post(
            "/api/device-types",
            json={"name": "PC", "description": "Gaming PC"},
        )
        assert resp.status_code == 403
