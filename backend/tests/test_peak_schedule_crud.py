"""Integration tests for Peak/Off-Peak Schedules CRUD (admin-gated)."""

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
        # Create a PEAK schedule
        resp = await client.post(
            "/api/schedules",
            json={
                "name": "Evening Peak",
                "is_peak": True,
                "day_of_week": 4,  # Friday
                "start_time": "18:00",
                "end_time": "22:00",
                "surcharge_paise": 500,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Evening Peak"
        assert data["is_peak"] is True
        peak_id = data["id"]

        # Create an OFF-PEAK schedule (is_peak=false)
        resp = await client.post(
            "/api/schedules",
            json={
                "name": "Morning Off-Peak",
                "is_peak": False,
                "day_of_week": None,
                "start_time": "06:00",
                "end_time": "10:00",
                "surcharge_paise": 0,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Morning Off-Peak"
        assert data["is_peak"] is False
        off_peak_id = data["id"]

        # GET list returns both (length >= 2)
        resp = await client.get("/api/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        assert any(s["id"] == peak_id for s in data)
        assert any(s["id"] == off_peak_id for s in data)


class TestGetAndUpdate:
    async def test_get_and_update(self, client: AsyncClient) -> None:
        # Create a schedule
        resp = await client.post(
            "/api/schedules",
            json={
                "name": "Weekend Peak",
                "is_peak": True,
                "day_of_week": 5,  # Saturday
                "start_time": "14:00",
                "end_time": "20:00",
                "surcharge_paise": 300,
            },
        )
        assert resp.status_code == 201
        schedule_id = resp.json()["id"]

        # GET /{id} -> 200
        resp = await client.get(f"/api/schedules/{schedule_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Weekend Peak"
        assert data["is_peak"] is True
        assert data["surcharge_paise"] == 300

        # PUT /{id} with {"surcharge_paise": 500} -> 200,
        # surcharge updated, name unchanged
        resp = await client.put(
            f"/api/schedules/{schedule_id}",
            json={"surcharge_paise": 500},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["surcharge_paise"] == 500
        assert data["name"] == "Weekend Peak"
        assert data["is_peak"] is True


class TestDelete:
    async def test_delete(self, client: AsyncClient) -> None:
        # Create a schedule
        resp = await client.post(
            "/api/schedules",
            json={
                "name": "To Delete",
                "is_peak": True,
                "day_of_week": 0,
                "start_time": "10:00",
                "end_time": "12:00",
                "surcharge_paise": 200,
            },
        )
        assert resp.status_code == 201
        schedule_id = resp.json()["id"]

        # DELETE /{id} -> 204
        resp = await client.delete(f"/api/schedules/{schedule_id}")
        assert resp.status_code == 204

        # GET /{id} -> 404
        resp = await client.get(f"/api/schedules/{schedule_id}")
        assert resp.status_code == 404


class TestAuthZoning:
    async def test_cashier_rejected(self, cashier_client: AsyncClient) -> None:
        # cashier -> 403 on POST
        resp = await cashier_client.post(
            "/api/schedules",
            json={
                "name": "Cashier Peak",
                "is_peak": True,
                "day_of_week": 1,
                "start_time": "10:00",
                "end_time": "12:00",
                "surcharge_paise": 100,
            },
        )
        assert resp.status_code == 403
