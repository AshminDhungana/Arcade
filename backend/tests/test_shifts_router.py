"""Integration tests for the Shift API router."""

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
    """Minimal staff stand-in.

    ``deps`` only reads ``.role``; the router only reads ``.id``. The isolated
    engine below has FK enforcement disabled, so the non-persisted id is fine.
    """

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
async def cashier_client(
    db: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_open_shift_201(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post("/api/shifts/open", json={"float_paise": 5000})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "OPEN"
    assert body["float_paise"] == 5000


async def test_duplicate_open_409(cashier_client: AsyncClient) -> None:
    await cashier_client.post("/api/shifts/open", json={"float_paise": 5000})
    resp = await cashier_client.post("/api/shifts/open", json={"float_paise": 5000})
    assert resp.status_code == 409


async def test_get_current_returns_open(cashier_client: AsyncClient) -> None:
    await cashier_client.post("/api/shifts/open", json={"float_paise": 5000})
    resp = await cashier_client.get("/api/shifts/current")
    assert resp.status_code == 200
    assert resp.json()["status"] == "OPEN"


async def test_close_shift_200(cashier_client: AsyncClient) -> None:
    await cashier_client.post("/api/shifts/open", json={"float_paise": 5000})
    resp = await cashier_client.post("/api/shifts/close", json={"counted_paise": 6500})
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLOSED"
    assert resp.json()["counted_paise"] == 6500


async def test_report_requires_admin(cashier_client: AsyncClient) -> None:
    open_resp = await cashier_client.post(
        "/api/shifts/open", json={"float_paise": 5000}
    )
    shift_id = open_resp.json()["id"]
    # cashier must be rejected (403) for the admin-only report
    resp = await cashier_client.get(f"/api/shifts/{shift_id}/report")
    assert resp.status_code == 403


async def test_report_200_for_admin(admin_client: AsyncClient) -> None:
    # admin opens + closes (admin passes require_cashier too), then reads report
    open_resp = await admin_client.post("/api/shifts/open", json={"float_paise": 5000})
    shift_id = open_resp.json()["id"]
    await admin_client.post("/api/shifts/close", json={"counted_paise": 6500})
    resp = await admin_client.get(f"/api/shifts/{shift_id}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["expected_cash_paise"] == 5000
    assert body["variance_paise"] == 1500
