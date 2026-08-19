"""Nightly SQLite backup service.

Copies the live ``arcade.db`` (with its WAL fully checkpointed into the main
file) into ``{backup_dir}/arcade_{YYYYMMDD_HHMM}.db`` and prunes files older
than ``backup_retain_days``. Mirrors the module-of-functions style of
``shift_service`` / ``audit_service``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.core.config import get_config
from backend.models._enums import AuditAction
from backend.services import audit_service

logger = logging.getLogger(__name__)

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
            for attempt in range(2):
                result = await conn.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
                row = result.fetchone()
                busy = row[0] if row else 0
                if busy == 0:
                    break
                logger.warning(
                    "wal_checkpoint(TRUNCATE) busy on attempt %d for %s",
                    attempt + 1,
                    src,
                )
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
    staff_id: str | None = None,
) -> BackupResult:
    """Copy the live DB to a timestamped file and prune old backups.

    :param db: Active session, used only for the audit log.
    :param source_db: Override the live source DB (used in tests).
    :param backup_dir: Override the destination dir (used in tests).
    :param retain_days: Override ``config.backup_retain_days`` (used in tests).
    :param staff_id: ID of the staff member who triggered the backup, if any
        (manual Admin trigger). System-initiated runs (scheduler) pass None.
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

    # Compute SHA256 of the backup file
    file_hash = hashlib.sha256(dst.read_bytes()).hexdigest()

    # Write .sha256 file (standard sha256sum format: "<hex_digest>  <filename>")
    sha256_path = dst.with_suffix(dst.suffix + ".sha256")
    sha256_path.write_text(f"{file_hash}  {dst.name}\n")

    # Update manifest.json atomically
    manifest_path = target_dir / "manifest.json"
    manifest = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    # Remove any existing entry for this filename (idempotent)
    manifest = [e for e in manifest if e["filename"] != dst.name]

    # Add new entry
    manifest.append(
        {
            "filename": dst.name,
            "sha256": file_hash,
            "size_bytes": dst.stat().st_size,
            "created_at": datetime.now(UTC).isoformat(),
            "staff_id": staff_id,
        }
    )

    # Atomic write
    tmp_path = manifest_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(manifest, indent=2))
    os.replace(tmp_path, manifest_path)

    await audit_service.log(
        db,
        action=AuditAction.BACKUP_CREATED,
        entity_type="backup",
        entity_id=dst.name,
        staff_id=staff_id,
        detail=f"path={dst};size={dst_size}",
    )

    retain = retain_days if retain_days is not None else config.backup_retain_days
    pruned = await prune_old_backups(
        db, backup_dir=target_dir, retain_days=retain, staff_id=staff_id
    )
    return BackupResult(backup_path=dst, pruned_count=pruned)


def verify_backup_integrity(backup_path: Path, manifest: list[dict[str, Any]]) -> bool:
    """Verify backup file SHA256 matches manifest entry."""
    entry = next((e for e in manifest if e["filename"] == backup_path.name), None)
    if not entry:
        return False
    file_hash = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    sha256_value = entry.get("sha256")
    if not isinstance(sha256_value, str):
        return False
    return file_hash == sha256_value


def load_manifest(backup_dir: Path) -> list[dict[str, Any]]:
    """Load manifest.json from backup directory."""
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text())
    if not isinstance(data, list):
        return []
    return data


async def prune_old_backups(
    db: AsyncSession,
    *,
    backup_dir: Path | None = None,
    retain_days: int | None = None,
    now: datetime | None = None,
    staff_id: str | None = None,
) -> int:
    """Delete backup files older than ``retain_days``; audit ``BACKUP_PRUNED``.

    Only files matching ``arcade_{YYYYMMDD_HHMM}.db`` are considered, so a
    stray ``notes.txt`` in the backup dir is never deleted.

    :param staff_id: ID of the staff member who triggered the prune, if any
        (manual Admin trigger). System-initiated runs pass None.
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
                # Also delete corresponding .sha256 file
                sha256_f = f.with_suffix(f.suffix + ".sha256")
                if sha256_f.exists():
                    sha256_f.unlink()
                deleted += 1

    if deleted:
        await audit_service.log(
            db,
            action=AuditAction.BACKUP_PRUNED,
            entity_type="backup",
            entity_id="prune",
            staff_id=staff_id,
            detail=f"deleted={deleted};retain_days={retain}",
        )

    # After deletions, rebuild manifest to only include existing files
    manifest_path = target_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        # Keep only entries for files that still exist
        existing_names = {f.name for f in target_dir.glob("arcade_*.db")}
        manifest = [e for e in manifest if e["filename"] in existing_names]
        tmp_path = manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(manifest, indent=2))
        os.replace(tmp_path, manifest_path)

    return deleted
