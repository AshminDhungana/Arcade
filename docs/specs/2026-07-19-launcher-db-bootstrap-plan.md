# Launcher DB Bootstrap & Schema-Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the `no such column: seats.agent_secret` startup crash by (1) adding the missing Alembic migration for four `Seat` columns and (2) giving the launcher a missing-DB bootstrap flow (restore latest backup / create new) that always finishes by migrating the DB to head.

**Architecture:** A new pure-logic module `backend/core/db_bootstrap.py` detects DB presence, finds/restores the latest backup, or creates a fresh DB, and calls `run_migrations(db_url=...)` to guarantee schema sync. The launcher's `_check_and_route` calls it before showing `MainScreen`; on a missing DB it opens a blocking modal so the user chooses. A new Alembic migration at the current head adds the four drifted `nullable` columns.

**Tech Stack:** Python 3.13, SQLAlchemy 2.0 (async), Alembic, aiosqlite, CustomTkinter, pytest (with `pytest-asyncio`), existing repo test conventions.

## Global Constraints

- **Root cause:** `Seat` declares four columns with **no migration**: `agent_secret` (`String(64)`), `enroll_code_hash` (`String(255)`), `enroll_code_expires_at` (`DateTime(timezone=True)`), `override_code_hash` (`String(255)`).
- **Migration must be purely additive:** all four columns `nullable=True`, matching the model — no `server_default`, no backfill.
- **Restore/create MUST delete `arcade.db-wal` and `arcade.db-shm`** so a stale WAL cannot replay and resurrect the old schema.
- **Backup location:** `backup_dir` default `./backups` (project root); backup files named `arcade_YYYYMMDD_HHMM.db`, matched by `^arcade_(\d{8}_\d{4})\.db$`.
- **Bootstrap scope:** the launcher only handles a missing DB *after* a valid license **and** `arcade.config.json` exist (the path that would show `MainScreen`).
- **Server safety net:** `main.py` lifespan keeps `run_migrations()`; bootstrap and server do not conflict (Alembic is idempotent).
- **DB path:** `<repo>/backend/arcade.db` (both `database.py` and the launcher's `_db_path()` resolve here).

---

### Task 1: Migrate the four drifted `Seat` columns

**Files:**
- Create: `backend/alembic/versions/f5a6b7c8d9e0_add_seat_selfprovisioning_columns.py`
- Test: `backend/tests/test_seat_migration.py`

**Interfaces:**
- Consumes: existing migration chain (current head `d6e7f8a9b0c1`); `backend/models/seat.py` column definitions.
- Produces: a new head revision `f5a6b7c8d9e0` adding the four columns — required by Task 2's `create_fresh_database` / `restore_latest_backup` to produce a bootable DB.

- [ ] **Step 1: Write the failing schema-guard test**

```python
# backend/tests/test_seat_migration.py
"""Regression tests for the 'no such column: seats.agent_secret' crash.

Every column declared on a SQLAlchemy model must be present in the
database after `alembic upgrade head`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command as alembic_command
from alembic.config import Config

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_ALEMBIC_DIR = Path(__file__).resolve().parent.parent / "alembic"

_NEW_COLUMNS = (
    "agent_secret",
    "enroll_code_hash",
    "enroll_code_expires_at",
    "override_code_hash",
)


def _upgrade_head(db_path: Path) -> None:
    cfg = Config(_ALEMBIC_INI)
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    alembic_command.upgrade(cfg, "head")


def _seat_columns(db_path: Path) -> set[str]:
    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        return {
            r[1]
            for r in conn.execute(sa.text("PRAGMA table_info(seats)")).fetchall()
        }


def test_seat_selfprovisioning_columns_present_after_head(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    _upgrade_head(db)
    cols = _seat_columns(db)
    for col in _NEW_COLUMNS:
        assert col in cols


def test_no_model_columns_drifted_after_head(tmp_path: Path) -> None:
    """Every model column must exist in the migrated DB (catches any drift)."""
    from backend.models import Base

    db = tmp_path / "verify.db"
    _upgrade_head(db)
    engine = sa.create_engine(f"sqlite:///{db}")
    with engine.connect() as conn:
        existing = {
            t: {
                r[1]
                for r in conn.execute(sa.text(f"PRAGMA table_info({t})")).fetchall()
            }
            for t in sa.inspect(engine).get_table_names()
        }
    for table, columns in Base.metadata.tables.items():
        for col in columns.columns:
            assert col.name in existing.get(table, set()), (
                f"Drifted column missing from DB: {table}.{col.name}"
            )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest backend/tests/test_seat_migration.py -v`
Expected: FAIL — `assert 'agent_secret' in cols` (and `test_no_model_columns_drifted_after_head` fails with `Drifted column missing from DB: seats.agent_secret`), because the four columns have no migration yet.

- [ ] **Step 3: Write the migration**

```python
# backend/alembic/versions/f5a6b7c8d9e0_add_seat_selfprovisioning_columns.py
"""add_seat_selfprovisioning_columns

Revision ID: f5a6b7c8d9e0
Revises: d6e7f8a9b0c1
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: str | Sequence[str] | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("seats", sa.Column("agent_secret", sa.String(64), nullable=True))
    op.add_column("seats", sa.Column("enroll_code_hash", sa.String(255), nullable=True))
    op.add_column(
        "seats",
        sa.Column("enroll_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("seats", sa.Column("override_code_hash", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("seats", "override_code_hash")
    op.drop_column("seats", "enroll_code_expires_at")
    op.drop_column("seats", "enroll_code_hash")
    op.drop_column("seats", "agent_secret")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest backend/tests/test_seat_migration.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/f5a6b7c8d9e0_add_seat_selfprovisioning_columns.py backend/tests/test_seat_migration.py
git commit -m "fix(db): add migration for drifted Seat self-provisioning columns"
```

---

### Task 2: `backend/core/db_bootstrap.py` + unit tests

**Files:**
- Modify: `backend/core/startup.py` (extend `run_migrations` to accept `db_url`)
- Create: `backend/core/db_bootstrap.py`
- Test: `backend/tests/test_db_bootstrap.py`

**Interfaces:**
- Consumes: `run_migrations` from `backend/core/startup.py` (modified in this task to accept `db_url`); `Base.metadata` via Alembic env; `backend/arcade.db` path.
- Produces: `is_db_present()`, `find_latest_backup(backup_dir)`, `restore_latest_backup(backup_dir)`, `create_fresh_database()`, `ensure_schema_current()` — consumed by Task 3's launcher integration.

- [ ] **Step 1: Extend `run_migrations` to accept a target DB URL**

In `backend/core/startup.py`, change the signature and URL resolution:

```python
async def run_migrations(db_url: str | None = None) -> None:
    """Run ``alembic upgrade head`` programmatically.

    :param db_url: Optional SQLAlchemy URL to migrate. Defaults to the live
        app engine URL. The launcher passes the resolved ``arcade.db`` path so
        it migrates exactly the database it restored/created.
    """
    from backend.core.database import async_engine

    here = Path(__file__).resolve().parent
    alembic_ini = here.parent / "alembic.ini"
    alembic_cfg = AlembicConfig(alembic_ini)
    alembic_cfg.set_main_option("script_location", str(here.parent / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url or str(async_engine.url))
    logger.info("Running database migrations ...")
    await asyncio.to_thread(alembic_command.upgrade, alembic_cfg, "head")
    logger.info("Migrations complete.")
```

This is backward-compatible: `main.py` and `_seed_default_staff` call `run_migrations()` with no argument.

- [ ] **Step 2: Write the failing tests**

```python
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
            r[1]
            for r in conn.execute(sa.text("PRAGMA table_info(seats)")).fetchall()
        }
    for c in (
        "agent_secret",
        "enroll_code_hash",
        "enroll_code_expires_at",
        "override_code_hash",
    ):
        assert c in cols
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pytest backend/tests/test_db_bootstrap.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.core.db_bootstrap'` (module not created yet).

- [ ] **Step 4: Write `backend/core/db_bootstrap.py`**

```python
# backend/core/db_bootstrap.py
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
        sidecar.unlink(missing_ok=True)


def restore_latest_backup(backup_dir: str | Path) -> Path:
    """Copy the newest backup over ``arcade.db`` (atomic) and migrate to head.

    Removes ``arcade.db-wal`` / ``arcade.db-shm`` first so a stale WAL cannot
    replay and resurrect an old schema. Raises ``FileNotFoundError`` if no
    backup exists.
    """
    latest = find_latest_backup(backup_dir)
    if latest is None:
        raise FileNotFoundError("No database backups found to restore")
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    _clear_sidecars(db)
    tmp = db.with_name(db.name + ".restore.tmp")
    try:
        shutil.copy2(latest, tmp)
        tmp.replace(db)
    finally:
        tmp.unlink(missing_ok=True)
    logger.info("Restored database from backup %s", latest.name)
    _migrate_to_head()
    return db


def create_fresh_database() -> Path:
    """Remove any stale DB + sidecars and create a fresh, migrated schema."""
    db = _db_path()
    db.unlink(missing_ok=True)
    _clear_sidecars(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Creating fresh database at %s", db)
    _migrate_to_head()
    return db


def ensure_schema_current() -> None:
    """Idempotently migrate an existing DB to head (defense-in-depth)."""
    _migrate_to_head()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest backend/tests/test_db_bootstrap.py -v`
Expected: PASS (all six tests, including the real-migration `test_create_fresh_database_produces_migrated_schema`).

- [ ] **Step 6: Commit**

```bash
git add backend/core/startup.py backend/core/db_bootstrap.py backend/tests/test_db_bootstrap.py
git commit -m "feat(core): add db_bootstrap module for launcher DB restore/create"
```

---

### Task 3: Launcher integration — modal + routing

**Files:**
- Modify: `launcher.py` (`_check_and_route`, plus new `_ensure_database` and `_ask_db_restore` methods on `LauncherApp`)
- Test: `backend/tests/test_launcher.py` (new `TestDatabaseBootstrap` class)

**Interfaces:**
- Consumes: `db_bootstrap` functions from Task 2; `load_config().backup_dir` from `backend.core.config`; `find_latest_backup`/`restore_latest_backup`/`create_fresh_database`/`ensure_schema_current`/`is_db_present`.
- Produces: launcher boots cleanly from present / restored / fresh DBs; modal shown only when `arcade.db` is missing.

- [ ] **Step 1: Write the failing routing tests**

Add to `backend/tests/test_launcher.py` (inside the same file; reuse the existing `_TK_AVAILABLE` skip guard and helpers):

```python
@pytest.mark.skipif(not _TK_AVAILABLE, reason="Tcl/Tk not available")
class TestDatabaseBootstrap:
    def test_missing_db_routes_to_main_after_restore_choice(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        import tkinter as tk

        from launcher import LauncherApp, MainScreen

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("launcher._db_path", lambda: tmp_path / "arcade.db")
        monkeypatch.setattr("backend.core.db_bootstrap.is_db_present", lambda: False)
        monkeypatch.setattr(
            "backend.core.db_bootstrap.find_latest_backup",
            lambda bd: tmp_path / "arcade_20260718_0300.db",
        )
        monkeypatch.setattr(
            "backend.core.db_bootstrap.restore_latest_backup", lambda bd: None
        )
        monkeypatch.setattr(
            "backend.core.db_bootstrap.ensure_schema_current", lambda: None
        )
        monkeypatch.setattr(
            LauncherApp, "_ask_db_restore", lambda self, latest: "restore"
        )
        monkeypatch.setattr(
            "backend.core.config.load_config",
            lambda: type("C", (), {"backup_dir": "./backups"})(),
        )
        monkeypatch.setattr(
            "launcher.check_license",
            lambda: type("R", (), {"ok": True, "payload": {}})(),
        )
        (tmp_path / "arcade.config.json").write_text("{}")

        shown: list = []
        monkeypatch.setattr(
            LauncherApp, "show_screen",
            lambda self, cls, *a, **k: shown.append(cls),
        )

        root = tk.Tk()
        app = LauncherApp(root)
        app._check_and_route()
        assert shown == [MainScreen]
        root.destroy()

    def test_present_db_routes_to_main_after_ensure_schema(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        import tkinter as tk

        from launcher import LauncherApp, MainScreen

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("launcher._db_path", lambda: tmp_path / "arcade.db")
        monkeypatch.setattr("backend.core.db_bootstrap.is_db_present", lambda: True)
        ensured: dict[str, bool] = {}
        monkeypatch.setattr(
            "backend.core.db_bootstrap.ensure_schema_current",
            lambda: ensured.update(called=True),
        )
        monkeypatch.setattr(
            "backend.core.config.load_config",
            lambda: type("C", (), {"backup_dir": "./backups"})(),
        )
        monkeypatch.setattr(
            "launcher.check_license",
            lambda: type("R", (), {"ok": True, "payload": {}})(),
        )
        (tmp_path / "arcade.config.json").write_text("{}")

        shown: list = []
        monkeypatch.setattr(
            LauncherApp, "show_screen",
            lambda self, cls, *a, **k: shown.append(cls),
        )

        root = tk.Tk()
        app = LauncherApp(root)
        app._check_and_route()
        assert shown == [MainScreen]
        assert ensured.get("called") is True
        root.destroy()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest backend/tests/test_launcher.py::TestDatabaseBootstrap -v`
Expected: FAIL — `AttributeError: 'LauncherApp' object has no attribute '_ensure_database'` (the routing does not yet call bootstrap; `_check_and_route` goes straight to `show_screen(MainScreen)` without the DB check).

- [ ] **Step 3: Add `_ensure_database` and `_ask_db_restore` to `LauncherApp`, and call them from `_check_and_route`**

In `launcher.py`, modify `_check_and_route` (currently around lines 813–822) to call `_ensure_database()` before showing `MainScreen`:

```python
    def _check_and_route(self) -> None:
        result = check_license()
        if result.ok:
            if Path("arcade.config.json").exists():
                self._ensure_database()
                self.show_screen(MainScreen)
                self._main_screen = self.current_screen
            else:
                self.show_screen(SetupWizard, result)
        else:
            self.show_screen(ActivationScreen, result)
```

Add the two new methods (place them just before `_check_and_route`):

```python
    def _ensure_database(self) -> None:
        """Ensure a valid, migrated arcade.db exists before the server starts.

        - Present DB -> ensure schema is current.
        - Missing DB  -> ask the user to restore the latest backup or create new.
        - Cancelled   -> quit the launcher (never boot a broken/absent DB).
        """
        from backend.core import db_bootstrap
        from backend.core.config import load_config

        if db_bootstrap.is_db_present():
            db_bootstrap.ensure_schema_current()
            return

        backup_dir = load_config().backup_dir
        latest = db_bootstrap.find_latest_backup(backup_dir)
        choice = self._ask_db_restore(latest)
        if choice == "restore" and latest is not None:
            try:
                db_bootstrap.restore_latest_backup(backup_dir)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(
                    "Restore failed",
                    f"Could not restore the backup:\n{exc}\n\n"
                    "A new empty database will be created instead.",
                )
                db_bootstrap.create_fresh_database()
        elif choice == "create":
            db_bootstrap.create_fresh_database()
        else:
            # User dismissed the dialog without choosing: do not start server.
            self.root.destroy()

    def _ask_db_restore(self, latest: Path | None) -> str:
        """Blocking modal: 'restore latest backup' / 'create new' / 'cancel'.

        Returns one of 'restore', 'create', or 'cancel'.
        """
        response: dict[str, str] = {"choice": "cancel"}

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Database Not Found")
        dialog.geometry("520x340")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        _center_window(dialog, 520, 340)

        ctk.CTkLabel(
            dialog,
            text="No database found",
            font=heading_font(16),
            text_color=[L_TEXT, TEXT],
        ).pack(padx=24, pady=(24, 6))
        ctk.CTkLabel(
            dialog,
            text=(
                "Arcade could not find arcade.db. Restore the most recent "
                "backup, or start with a new (empty) database."
            ),
            font=body_font(12),
            text_color=MUTED_TEXT,
            wraplength=460,
            justify="left",
        ).pack(padx=24, pady=(0, 12))

        if latest is not None:
            ctk.CTkLabel(
                dialog,
                text=f"Latest backup: {latest.name}",
                font=mono_font(11),
                text_color=[L_TEXT, TEXT],
            ).pack(padx=24, pady=(0, 12))

        def _choose(value: str) -> None:
            response["choice"] = value
            dialog.grab_release()
            dialog.destroy()

        restore_btn = ctk.CTkButton(
            dialog,
            text="Restore latest backup",
            command=lambda: _choose("restore"),
            state="normal" if latest is not None else "disabled",
            font=heading_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            text_color=TEXT,
        )
        restore_btn.pack(fill="x", padx=24, pady=(4, 10))
        create_btn = ctk.CTkButton(
            dialog,
            text="Create new database",
            command=lambda: _choose("create"),
            font=heading_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=EMERALD,
            hover_color=EMERALD_HOVER,
            text_color=TEXT,
        )
        create_btn.pack(fill="x", padx=24, pady=(0, 10))
        cancel_btn = ctk.CTkButton(
            dialog,
            text="Cancel",
            command=lambda: _choose("cancel"),
            font=body_font(12),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=[L_BORDER, S700],
            hover_color=[L_BORDER, S700_HOVER],
            text_color=[L_TEXT, TEXT],
        )
        cancel_btn.pack(fill="x", padx=24, pady=(0, 16))

        dialog.protocol("WM_DELETE_WINDOW", lambda: _choose("cancel"))
        self.root.wait_window(dialog)
        return response["choice"]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest backend/tests/test_launcher.py::TestDatabaseBootstrap -v`
Expected: PASS (both routing tests).

- [ ] **Step 5: Run the full backend test suite**

Run: `pytest backend/tests/ -v`
Expected: PASS (no regressions; the new head migration + db_bootstrap tests pass).

- [ ] **Step 6: Manual verification of the modal (Tkinter, not headless-testable)**

From the repo root with the venv active:
1. Ensure `backend/arcade.db` does **not** exist (and no `-wal`/`-shm`).
2. Run `python launcher.py` with a valid `license.key` and existing `arcade.config.json`.
3. Confirm the "Database Not Found" modal appears with "Restore latest backup" (enabled only if `backups/` has a file) and "Create new database".
4. Choose "Create new database" → modal closes, `MainScreen` shows; start the server → boots without `no such column`.
5. Repeat with a backup present → "Restore latest backup" is enabled and shows the timestamp; choosing it restores and boots cleanly.
6. Dismiss the modal (Cancel / close) → launcher quits, no server started.

- [ ] **Step 7: Commit**

```bash
git add launcher.py backend/tests/test_launcher.py
git commit -m "feat(launcher): bootstrap DB on missing arcade.db with restore/create choice"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1 implements the four-column migration + the schema-drift guard (Spec §1, §5). Task 2 implements `db_bootstrap` (Spec §2). Task 3 implements the modal + routing (Spec §3) and edge cases — missing backups disable Restore (§4), restore failure falls back to create (§4), cancel quits (§3/§4). Server `run_migrations` safety net retained (§4). WAL/SHM removal covered in `restore`/`create` (§4).
- **No placeholders:** every step has concrete code or an exact command with expected output.
- **Type consistency:** `find_latest_backup(backup_dir)` and `restore_latest_backup(backup_dir)` take `str | Path` consistently; `is_db_present() -> bool`; `_ask_db_restore(latest) -> str` returning `'restore' | 'create' | 'cancel'`; `create_fresh_database() -> Path`. Launcher tests call these exact names/signatures.
- **Note on `docs/superpowers`:** the skill's default plan path (`docs/superpowers/plans/`) is gitignored in this repo (`docs/superpowers` in `.gitignore`), so this plan is saved under `docs/specs/` to stay committable, matching where the approved spec lives.
