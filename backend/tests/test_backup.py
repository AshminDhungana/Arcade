"""Unit tests for backend.services.backup_service."""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest_asyncio
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.models._enums import AuditAction
from backend.repositories import audit_repo
from backend.services import backup_service


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
async def source_db(tmp_path: Path) -> AsyncGenerator[Path]:
    """A real on-disk SQLite file (the 'live' DB) to back up."""
    src = tmp_path / "arcade.db"
    engine = create_async_engine(URL.create("sqlite+aiosqlite", database=str(src)))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    yield src


async def test_run_backup_creates_timestamped_file(
    db: AsyncSession, source_db: Path, tmp_path: Path
) -> None:
    backup_dir = tmp_path / "backups"
    result = await backup_service.run_backup(
        db, source_db=source_db, backup_dir=backup_dir
    )
    assert result.backup_path.parent == backup_dir
    assert re.fullmatch(r"arcade_\d{8}_\d{4}\.db", result.backup_path.name)
    assert result.backup_path.exists()
    # Copy must be byte-for-byte equal in size to the source.
    assert result.backup_path.stat().st_size == source_db.stat().st_size


async def test_run_backup_audits_backup_created(
    db: AsyncSession, source_db: Path, tmp_path: Path
) -> None:
    await backup_service.run_backup(
        db, source_db=source_db, backup_dir=tmp_path / "backups"
    )
    logs = await audit_repo.list(db, action=AuditAction.BACKUP_CREATED.value)
    assert len(logs) == 1
    assert logs[0].entity_type == "backup"
    assert re.fullmatch(r"arcade_\d{8}_\d{4}\.db", logs[0].entity_id)


async def test_prune_deletes_only_old_matching_files(
    db: AsyncSession, tmp_path: Path
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    old = backup_dir / "arcade_20200101_0100.db"
    old.write_bytes(b"old")
    keep = backup_dir / "arcade_20990101_0100.db"
    keep.write_bytes(b"new")
    stray = backup_dir / "notes.txt"
    stray.write_bytes(b"do-not-touch")

    deleted = await backup_service.prune_old_backups(
        db,
        backup_dir=backup_dir,
        retain_days=7,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert deleted == 1
    assert not old.exists()
    assert keep.exists()
    assert stray.exists()  # non-matching file untouched


async def test_prune_audits_backup_pruned(db: AsyncSession, tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "arcade_20200101_0100.db").write_bytes(b"old")

    await backup_service.prune_old_backups(
        db,
        backup_dir=backup_dir,
        retain_days=7,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    logs = await audit_repo.list(db, action=AuditAction.BACKUP_PRUNED.value)
    assert len(logs) == 1
    assert "deleted=1" in (logs[0].detail or "")


async def test_prune_no_audit_when_nothing_deleted(
    db: AsyncSession, tmp_path: Path
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "arcade_20990101_0100.db").write_bytes(b"future")

    deleted = await backup_service.prune_old_backups(
        db,
        backup_dir=backup_dir,
        retain_days=7,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert deleted == 0
    logs = await audit_repo.list(db, action=AuditAction.BACKUP_PRUNED.value)
    assert len(logs) == 0
