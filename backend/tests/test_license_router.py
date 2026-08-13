"""Tests for POST /api/license/verify (admin-only, audited)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.licensing.verify import LicenseError, LicenseResult
from backend.main import app
from backend.models._enums import AuditAction, StaffRole
from backend.repositories import audit_repo


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


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_verify_license_requires_admin(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post("/api/license/verify")
    assert resp.status_code == 403


async def test_verify_license_returns_result_and_audits_ok(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    with patch("backend.api.routers.license.check_license") as mock_check:
        mock_check.return_value = LicenseResult(
            ok=True,
            error=None,
            payload={"hardware_id": "deadbeef", "license_type": "PERPETUAL"},
        )
        resp = await admin_client.post("/api/license/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["error"] is None
    assert body["payload"]["hardware_id"] == "deadbeef"

    logs = await audit_repo.list(db, action=AuditAction.LICENSE_CHECK.value)
    assert len(logs) == 1
    assert logs[0].entity_id == "deadbeef"
    assert logs[0].detail == "status=ok"
    assert logs[0].staff_id == "mock-staff-id"


async def test_verify_license_failure_audits_error(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    with patch("backend.api.routers.license.check_license") as mock_check:
        mock_check.return_value = LicenseResult(
            ok=False, error=LicenseError.MISSING, payload=None
        )
        resp = await admin_client.post("/api/license/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["error"] == "no license.key found"

    logs = await audit_repo.list(db, action=AuditAction.LICENSE_CHECK.value)
    assert len(logs) == 1
    assert logs[0].entity_id == "unknown"
    assert logs[0].detail == "status=error:no license.key found"
