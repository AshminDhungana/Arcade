"""Integration tests for the Backup API router."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff
from backend.core.database import Base, get_db
from backend.main import app
from backend.models._enums import StaffRole
from backend.services import backup_service


def _mock_staff(role: StaffRole) -> object:
    class _S:
        id = "mock-staff-id"
        name = "Mock"
        is_active = True
        token_version = 0
        role: StaffRole

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
async def admin_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.ADMIN)

    async def _fake_run_backup(
        *args: object, **kwargs: object
    ) -> backup_service.BackupResult:
        return backup_service.BackupResult(
            backup_path=Path("arcade_20260101_0300.db"), pruned_count=2
        )

    orig = backup_service.run_backup
    backup_service.run_backup = _fake_run_backup
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    backup_service.run_backup = orig
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def cashier_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_run_backup_200_for_admin(admin_client: AsyncClient) -> None:
    resp = await admin_client.post("/api/backup/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["backup_file"] == "arcade_20260101_0300.db"
    assert body["pruned_count"] == 2


async def test_run_backup_requires_admin(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post("/api/backup/run")
    assert resp.status_code == 403
