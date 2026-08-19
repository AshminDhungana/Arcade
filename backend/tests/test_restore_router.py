"""Unit tests for backend.api.routers.restore."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import URL
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
async def source_db(tmp_path: Path) -> Path:
    """A real on-disk SQLite file (the 'live' DB) to back up."""
    src = tmp_path / "arcade.db"
    engine = create_async_engine(URL.create("sqlite+aiosqlite", database=str(src)))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    return src


@pytest_asyncio.fixture
async def admin_client(
    db: AsyncSession, source_db: Path, tmp_path: Path
) -> AsyncGenerator[AsyncClient]:
    from backend.core.config import get_config

    config = get_config()
    config.backup_dir = str(tmp_path / "backups")

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.ADMIN)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def cashier_client(
    db: AsyncSession, source_db: Path, tmp_path: Path
) -> AsyncGenerator[AsyncClient]:
    from backend.core.config import get_config

    config = get_config()
    config.backup_dir = str(tmp_path / "backups")

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_restore_endpoint_returns_202_and_writes_signal(
    admin_client: AsyncClient, db: AsyncSession, source_db: Path, tmp_path: Path
) -> None:
    # Create a valid backup with manifest
    backup_dir = tmp_path / "backups"
    result = await backup_service.run_backup(
        db, source_db=source_db, backup_dir=backup_dir
    )
    backup_name = result.backup_path.name

    response = await admin_client.post(
        "/api/admin/restore",
        json={"backup_filename": backup_name},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["backup_file"] == backup_name
    assert "restore queued" in data["message"].lower()

    # Check signal file written
    signal_path = Path(".") / ".restore_requested"
    assert signal_path.exists()
    signal_data = json.loads(signal_path.read_text())
    assert signal_data["backup_filename"] == backup_name
    assert signal_data["requested_by"] == "mock-staff-id"

    # Clean up
    if signal_path.exists():
        signal_path.unlink()


async def test_restore_endpoint_validates_sha256(
    admin_client: AsyncClient, db: AsyncSession, source_db: Path, tmp_path: Path
) -> None:
    backup_dir = tmp_path / "backups"
    result = await backup_service.run_backup(
        db, source_db=source_db, backup_dir=backup_dir
    )
    backup_name = result.backup_path.name

    # Corrupt the backup file
    result.backup_path.write_bytes(b"corrupted")

    response = await admin_client.post(
        "/api/admin/restore",
        json={"backup_filename": backup_name},
    )

    assert response.status_code == 400
    assert (
        "sha256" in response.json()["detail"].lower()
        or "integrity" in response.json()["detail"].lower()
    )

    # Signal file should NOT be written
    signal_path = Path(".") / ".restore_requested"
    assert not signal_path.exists()


async def test_restore_endpoint_requires_admin(
    cashier_client: AsyncClient, db: AsyncSession, source_db: Path, tmp_path: Path
) -> None:
    backup_dir = tmp_path / "backups"
    result = await backup_service.run_backup(
        db, source_db=source_db, backup_dir=backup_dir
    )
    backup_name = result.backup_path.name

    response = await cashier_client.post(
        "/api/admin/restore",
        json={"backup_filename": backup_name},
    )

    assert response.status_code == 403


async def test_restore_endpoint_defaults_to_latest(
    admin_client: AsyncClient, db: AsyncSession, source_db: Path, tmp_path: Path
) -> None:
    import time

    backup_dir = tmp_path / "backups"
    await backup_service.run_backup(db, source_db=source_db, backup_dir=backup_dir)
    time.sleep(0.1)  # Ensure different timestamp
    result = await backup_service.run_backup(
        db, source_db=source_db, backup_dir=backup_dir
    )
    latest_name = result.backup_path.name

    response = await admin_client.post(
        "/api/admin/restore",
        json={},  # No backup_filename = latest
    )

    assert response.status_code == 202
    assert response.json()["backup_file"] == latest_name

    # Clean up
    signal_path = Path(".") / ".restore_requested"
    if signal_path.exists():
        signal_path.unlink()
