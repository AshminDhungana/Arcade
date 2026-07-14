"""Nightly SQLite backup service.

Copies the live ``arcade.db`` (with its WAL fully checkpointed into the main
file) into ``{backup_dir}/arcade_{YYYYMMDD_HHMM}.db`` and prunes files older
than ``backup_retain_days``. Mirrors the module-of-functions style of
``shift_service`` / ``audit_service``.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.core.config import get_config
from backend.models._enums import AuditAction
from backend.services import audit_service

# Matches backup filenames so pruning never touches unrelated files.
_BACKUP_NAME_RE = re.compile(r"^arcade_(\d{8}_\d{4})\.db$")


@dataclass(frozen=True)
class BackupResult:
    """Outcome of a single backup run."""

    backup_path: Path
    pruned_count: int


def _resolve_backup_dir(config_backup_dir: str) -> Path:
    """Resolve backup_dir relative to the project root (mirrors ``load_config``)."""
    p = Path(config_backup_dir)
    if p.is_absolute():
        return p
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / config_backup_dir


def _source_db_path() -> Path:
    """Path of the live database the engine is connected to."""
    from backend.core.database import async_engine

    db_path = async_engine.url.database
    if db_path is None:
        msg = "Live engine has no database path configured"
        raise RuntimeError(msg)
    return Path(db_path)


async def _checkpoint_and_copy(src: Path, dst: Path) -> tuple[int, int]:
    """Flush WAL into the main db file, copy it, return (src_size, dst_size).

    A separate connection is used so the same code path works whether ``src``
    is the live engine DB or an explicit test file.
    """
    chk = create_async_engine(URL.create("sqlite+aiosqlite", database=str(src)))
    try:
        async with chk.connect() as conn:
            await conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        await chk.dispose()
    shutil.copy2(src, dst)
    return src.stat().st_size, dst.stat().st_size


async def run_backup(
    db: AsyncSession,
    *,
    source_db: Path | None = None,
    backup_dir: Path | None = None,
    retain_days: int | None = None,
) -> BackupResult:
    """Copy the live DB to a timestamped file and prune old backups.

    :param db: Active session, used only for the audit log.
    :param source_db: Override the live source DB (used in tests).
    :param backup_dir: Override the destination dir (used in tests).
    :param retain_days: Override ``config.backup_retain_days`` (used in tests).
    """
    config = get_config()
    src = source_db or _source_db_path()
    target_dir = backup_dir or _resolve_backup_dir(config.backup_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M")
    dst = target_dir / f"arcade_{stamp}.db"

    src_size, dst_size = await _checkpoint_and_copy(src, dst)
    if src_size != dst_size:
        msg = (
            f"Backup integrity check failed: source {src_size} bytes "
            f"!= copy {dst_size} bytes"
        )
        raise RuntimeError(msg)

    await audit_service.log(
        db,
        action=AuditAction.BACKUP_CREATED,
        entity_type="backup",
        entity_id=dst.name,
        detail=f"path={dst};size={dst_size}",
    )

    retain = retain_days if retain_days is not None else config.backup_retain_days
    pruned = await prune_old_backups(db, backup_dir=target_dir, retain_days=retain)
    return BackupResult(backup_path=dst, pruned_count=pruned)


async def prune_old_backups(
    db: AsyncSession,
    *,
    backup_dir: Path | None = None,
    retain_days: int | None = None,
    now: datetime | None = None,
) -> int:
    """Delete backup files older than ``retain_days``; audit ``BACKUP_PRUNED``.

    Only files matching ``arcade_{YYYYMMDD_HHMM}.db`` are considered, so a
    stray ``notes.txt`` in the backup dir is never deleted.
    """
    config = get_config()
    target_dir = backup_dir or _resolve_backup_dir(config.backup_dir)
    retain = retain_days if retain_days is not None else config.backup_retain_days
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retain)

    deleted = 0
    if target_dir.exists():
        for f in target_dir.glob("arcade_*.db"):
            m = _BACKUP_NAME_RE.match(f.name)
            if not m:
                continue
            try:
                ftime = datetime.strptime(m.group(1), "%Y%m%d_%H%M").replace(tzinfo=UTC)
            except ValueError:
                continue
            if ftime < cutoff:
                f.unlink()
                deleted += 1

    if deleted:
        await audit_service.log(
            db,
            action=AuditAction.BACKUP_PRUNED,
            entity_type="backup",
            entity_id="prune",
            detail=f"deleted={deleted};retain_days={retain}",
        )
    return deleted
