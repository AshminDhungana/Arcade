"""Integration tests for the Staff Management API router."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.security import hash_pin, verify_pin
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
async def self_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db, name="Self", pin_hash=hash_pin("1234"), role=StaffRole.CASHIER.value
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


@pytest_asyncio.fixture
async def self_client(
    db: AsyncSession, self_staff: Staff
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: self_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


class TestCreateStaff:
    async def test_create_admin_success(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/staff", json={"name": "Hire", "role": "CASHIER", "pin": "1234"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Hire"
        assert data["role"] == "CASHIER"
        assert data["is_active"] is True
        assert "pin_hash" not in data
        assert "token_version" not in data

    async def test_create_cashier_forbidden(self, cashier_client: AsyncClient) -> None:
        resp = await cashier_client.post(
            "/api/staff", json={"name": "Hire", "role": "CASHIER", "pin": "1234"}
        )
        assert resp.status_code == 403

    async def test_create_pin_too_short(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/staff", json={"name": "Hire", "role": "CASHIER", "pin": "12"}
        )
        assert resp.status_code == 422


class TestUpdatePin:
    async def test_update_pin_self_success(
        self, self_client: AsyncClient, self_staff: Staff, db: AsyncSession
    ) -> None:
        resp = await self_client.patch(
            f"/api/staff/{self_staff.id}/pin", json={"pin": "5678"}
        )
        assert resp.status_code == 200
        refreshed = await staff_repo.get_by_id(db, self_staff.id)
        assert refreshed.token_version == 1
        assert verify_pin("5678", refreshed.pin_hash) is True

    async def test_update_pin_admin_for_other_success(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        target = await staff_repo.create(
            db, name="T", pin_hash=hash_pin("1111"), role=StaffRole.CASHIER.value
        )
        resp = await client.patch(f"/api/staff/{target.id}/pin", json={"pin": "2222"})
        assert resp.status_code == 200
        refreshed = await staff_repo.get_by_id(db, target.id)
        assert refreshed.token_version == 1

    async def test_update_pin_other_cashier_forbidden(
        self, cashier_client: AsyncClient, db: AsyncSession
    ) -> None:
        target = await staff_repo.create(
            db, name="Victim", pin_hash=hash_pin("1111"), role=StaffRole.CASHIER.value
        )
        resp = await cashier_client.patch(
            f"/api/staff/{target.id}/pin", json={"pin": "2222"}
        )
        assert resp.status_code == 403

    async def test_update_pin_not_found(self, client: AsyncClient) -> None:
        resp = await client.patch("/api/staff/nonexistent/pin", json={"pin": "2222"})
        assert resp.status_code == 404

    async def test_update_pin_too_short(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        target = await staff_repo.create(
            db, name="T2", pin_hash=hash_pin("1111"), role=StaffRole.CASHIER.value
        )
        resp = await client.patch(f"/api/staff/{target.id}/pin", json={"pin": "12"})
        assert resp.status_code == 422


class TestDeactivate:
    async def test_deactivate_admin_success(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        target = await staff_repo.create(
            db, name="Deact", pin_hash=hash_pin("1111"), role=StaffRole.CASHIER.value
        )
        resp = await client.patch(f"/api/staff/{target.id}/deactivate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is False
        refreshed = await staff_repo.get_by_id(db, target.id)
        assert refreshed.is_active is False
        assert refreshed.token_version == 1

    async def test_deactivate_cashier_forbidden(
        self, cashier_client: AsyncClient, db: AsyncSession
    ) -> None:
        target = await staff_repo.create(
            db, name="Deact2", pin_hash=hash_pin("1111"), role=StaffRole.CASHIER.value
        )
        resp = await cashier_client.patch(f"/api/staff/{target.id}/deactivate")
        assert resp.status_code == 403

    async def test_deactivate_not_found(self, client: AsyncClient) -> None:
        resp = await client.patch("/api/staff/nonexistent/deactivate")
        assert resp.status_code == 404


class TestListStaff:
    async def test_list_admin_success(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await staff_repo.create(
            db, name="L1", pin_hash=hash_pin("1"), role=StaffRole.CASHIER.value
        )
        await staff_repo.create(
            db, name="L2", pin_hash=hash_pin("1"), role=StaffRole.ADMIN.value
        )
        resp = await client.get("/api/staff")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # admin_staff + 2
        for s in data:
            assert "pin_hash" not in s
            assert "token_version" not in s

    async def test_list_cashier_forbidden(self, cashier_client: AsyncClient) -> None:
        resp = await cashier_client.get("/api/staff")
        assert resp.status_code == 403
