# backend/tests/test_db_bootstrap.py
from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa

from backend.core import db_bootstrap


def test_is_db_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "arcade.db"
    monkeypatch.setattr(db_bootstrap, "_db_path", lambda: db)
    assert db_bootstrap.is_db_present() is False
    db.write_text("x")
    assert db_bootstrap.is_db_present() is True


def test_find_latest_backup_picks_newest(tmp_path: Path) -> None:
    d = tmp_path / "backups"
    d.mkdir()
    (d / "arcade_20220101_0000.db").write_text("old")
    (d / "arcade_20260101_0000.db").write_text("mid")
    (d / "arcade_20260718_0300.db").write_text("new")
    (d / "notes.txt").write_text("ignore")
    latest = db_bootstrap.find_latest_backup(d)
    assert latest is not None
    assert latest.name == "arcade_20260718_0300.db"


def test_find_latest_backup_none_when_empty(tmp_path: Path) -> None:
    assert db_bootstrap.find_latest_backup(tmp_path / "nope") is None


def test_restore_latest_backup_copies_and_clears_sidecars(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "arcade_20260101_0000.db").write_bytes(b"OLD")
    (backup_dir / "arcade_20260718_0300.db").write_bytes(b"BACKUP")

    db = tmp_path / "arcade.db"
    db.write_bytes(b"STALE")
    (tmp_path / "arcade.db-wal").write_bytes(b"WAL")
    (tmp_path / "arcade.db-shm").write_bytes(b"SHM")

    monkeypatch.setattr(db_bootstrap, "_db_path", lambda: db)
    monkeypatch.setattr(db_bootstrap, "_migrate_to_head", lambda: None)

    result = db_bootstrap.restore_latest_backup(backup_dir)
    assert result == db
    assert db.read_bytes() == b"BACKUP"
    assert not (tmp_path / "arcade.db-wal").exists()
    assert not (tmp_path / "arcade.db-shm").exists()


def test_restore_without_backup_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(db_bootstrap, "_db_path", lambda: tmp_path / "arcade.db")
    with pytest.raises(FileNotFoundError):
        db_bootstrap.restore_latest_backup(tmp_path / "empty")


def test_create_fresh_database_removes_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "arcade.db"
    db.write_bytes(b"OLD")
    (tmp_path / "arcade.db-wal").write_bytes(b"WAL")
    monkeypatch.setattr(db_bootstrap, "_db_path", lambda: db)
    monkeypatch.setattr(db_bootstrap, "_migrate_to_head", lambda: None)
    db_bootstrap.create_fresh_database()
    assert not db.exists()  # mocked migration => not recreated
    assert not (tmp_path / "arcade.db-wal").exists()


def test_create_fresh_database_produces_migrated_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: real migration against a temp DB yields the 4 columns."""
    db = tmp_path / "arcade.db"
    monkeypatch.setattr(db_bootstrap, "_db_path", lambda: db)
    db_bootstrap.create_fresh_database()
    assert db.exists()
    engine = sa.create_engine(f"sqlite:///{db}")
    with engine.connect() as conn:
        cols = {
            r[1] for r in conn.execute(sa.text("PRAGMA table_info(seats)")).fetchall()
        }
    for c in (
        "agent_secret",
        "enroll_code_hash",
        "enroll_code_expires_at",
        "override_code_hash",
    ):
        assert c in cols
