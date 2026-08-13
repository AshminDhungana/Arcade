"""B.4 — Cashier is denied admin-only operations (403)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.main import app
from backend.models._enums import StaffRole


def _mock_staff(role: StaffRole) -> object:
    class _S:
        id = "mock-staff-id"
        name = "Mock"
        is_active = True
        token_version = 0

    s = _S()
    s.role = role
    return s


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def cashier_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_cashier_cannot_patch_settings(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.patch("/api/settings", json={"enable_members": "false"})
    assert resp.status_code == 403


async def test_cashier_cannot_toggle_feature_flag(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.patch(
        "/api/settings", json={"enable_reservations": "false"}
    )
    assert resp.status_code == 403


async def test_cashier_cannot_force_bulk_overlay(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post("/api/seats/bulk/overlay", json={"show": True})
    assert resp.status_code == 403


async def test_cashier_cannot_run_backup(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post("/api/backup/run")
    assert resp.status_code == 403


async def test_cashier_cannot_create_staff(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post(
        "/api/staff",
        json={"name": "Hacker", "role": "ADMIN", "pin": "1234", "is_active": True},
    )
    assert resp.status_code == 403


async def test_cashier_can_bill_pos(cashier_client: AsyncClient) -> None:
    """B.4 positive: cashier may bill + run POS (not blocked by admin gate)."""
    resp = await cashier_client.post("/api/pos/items")
    assert resp.status_code != 403
