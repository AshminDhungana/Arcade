"""Integration tests for Menu Item CRUD (admin-gated)."""

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


class TestCreateAndGet:
    async def test_create_and_get(self, client: AsyncClient) -> None:
        # Create menu item
        resp = await client.post(
            "/api/menu-items",
            json={
                "name": "Cold Coffee",
                "price_paise": 25000,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Cold Coffee"
        assert data["price_paise"] == 25000
        item_id = data["id"]

        # Get menu item
        resp = await client.get(f"/api/menu-items/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Cold Coffee"
        assert data["price_paise"] == 25000


class TestUpdate:
    async def test_update(self, client: AsyncClient) -> None:
        # Create menu item
        resp = await client.post(
            "/api/menu-items",
            json={
                "name": "Hot Coffee",
                "price_paise": 20000,
            },
        )
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        # Update menu item (PATCH-style: only is_available)
        resp = await client.put(
            f"/api/menu-items/{item_id}",
            json={"is_available": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_available"] is False
        # Unchanged fields
        assert data["name"] == "Hot Coffee"
        assert data["price_paise"] == 20000


class TestDelete:
    async def test_delete(self, client: AsyncClient) -> None:
        # Create menu item
        resp = await client.post(
            "/api/menu-items",
            json={
                "name": "Tea",
                "price_paise": 15000,
            },
        )
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        # Delete menu item
        resp = await client.delete(f"/api/menu-items/{item_id}")
        assert resp.status_code == 204

        # Verify 404 on GET
        resp = await client.get(f"/api/menu-items/{item_id}")
        assert resp.status_code == 404


class TestAuthZoning:
    async def test_cashier_rejected(self, cashier_client: AsyncClient) -> None:
        resp = await cashier_client.post(
            "/api/menu-items",
            json={
                "name": "Zone Y",
                "price_paise": 5000,
            },
        )
        assert resp.status_code == 403
