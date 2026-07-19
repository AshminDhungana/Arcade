"""Launcher-side database bootstrap.

When the live ``arcade.db`` is missing at launcher startup, decide what to
do: restore the latest backup, or create a fresh database. Every path ends
by running ``alembic upgrade head`` so the resulting database is
schema-synced with the SQLAlchemy models — this is what makes "restore
backup / create new" actually boot (see the design spec).

Pure logic, no UI, so it is unit-testable without Tkinter.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Matches backup filenames from backup_service.run_backup so we never mistake
# an unrelated file for a backup.
_BACKUP_NAME_RE = re.compile(r"^arcade_(\d{8}_\d{4})\.db$")


def _db_path() -> Path:
    """Path of the live database the launcher manages."""
    from backend.core.database import async_engine

    db = async_engine.url.database
    if db is None:
        return Path(__file__).resolve().parent.parent / "arcade.db"
    return Path(db)


def is_db_present() -> bool:
    """Return True if the live ``arcade.db`` file currently exists."""
    return _db_path().exists()


def _resolve_backup_dir(backup_dir: str | Path) -> Path:
    """Resolve a backup_dir (possibly relative) against the project root."""
    p = Path(backup_dir)
    if p.is_absolute():
        return p
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / p


def find_latest_backup(backup_dir: str | Path) -> Path | None:
    """Return the newest ``arcade_YYYYMMDD_HHMM.db`` backup, or None."""
    target = _resolve_backup_dir(backup_dir)
    if not target.exists():
        return None
    candidates: list[tuple[str, Path]] = []
    for f in target.glob("arcade_*.db"):
        m = _BACKUP_NAME_RE.match(f.name)
        if m:
            candidates.append((m.group(1), f))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _migrate_to_head() -> None:
    """Run ``alembic upgrade head`` synchronously against the live DB path.

    ``run_migrations`` is async and offloads Alembic to a worker thread; the
    launcher has no running event loop, so ``asyncio.run`` drives it. Passing
    the resolved ``arcade.db`` URL keeps the migration scoped to the DB we
    just restored/created.
    """
    from backend.core.startup import run_migrations

    asyncio.run(run_migrations(db_url=f"sqlite+aiosqlite:///{_db_path()}"))


def _sidecar_files(db: Path) -> list[Path]:
    return [db.with_name(db.name + "-wal"), db.with_name(db.name + "-shm")]


def _clear_sidecars(db: Path) -> None:
    for sidecar in _sidecar_files(db):
        try:
            sidecar.unlink()
        except FileNotFoundError:
            pass


def restore_latest_backup(backup_dir: str | Path) -> Path:
    """Atomic copy of the newest backup + clear WAL/SHM sidecars, then migrate.

    :param backup_dir: Directory containing ``arcade_YYYYMMDD_HHMM.db`` files.
    :return: Path to the live ``arcade.db`` that was restored.
    :raises FileNotFoundError: If no valid backup file is found.
    """
    backup = find_latest_backup(backup_dir)
    if backup is None:
        raise FileNotFoundError(f"No backup found in {backup_dir}")

    db = _db_path()
    target_dir = db.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # Atomic copy: write to temp then replace
    tmp = target_dir / f".{db.name}.tmp"
    shutil.copy2(backup, tmp)
    tmp.replace(db)

    # Clear any stale WAL/SHM so a stale WAL can't replay over our fresh DB
    _clear_sidecars(db)

    _migrate_to_head()
    logger.info("Restored backup %s -> %s and migrated to head", backup.name, db)
    return db


def create_fresh_database() -> Path:
    """Remove any existing DB + sidecars, create parent dirs, migrate to head.

    :return: Path to the freshly created and migrated ``arcade.db``.
    """
    db = _db_path()
    if db.exists():
        db.unlink()
    _clear_sidecars(db)

    db.parent.mkdir(parents=True, exist_ok=True)

    _migrate_to_head()
    logger.info("Created fresh database at %s and migrated to head", db)
    return db


def ensure_schema_current() -> Path:
    """Ensure the live DB exists and is at the current schema head.

    If the DB is missing, create a fresh one. If it exists, just migrate.
    Returns the live DB path either way.
    """
    db = _db_path()
    if not db.exists():
        return create_fresh_database()
    _migrate_to_head()
    return db
