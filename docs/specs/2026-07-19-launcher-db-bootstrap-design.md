# Launcher DB Bootstrap & Schema-Sync Design

**Date:** 2026-07-19
**Status:** Approved
**Components:** `launcher.py`, `backend/core/db_bootstrap.py` (new), `backend/alembic/versions/*` (new migration)

## Background & Root Cause

The server crashed on startup with:

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: seats.agent_secret
```

The crash is **schema drift, not a missing database file**. The `Seat` model
(`backend/models/seat.py:35-40`) defines four columns that no Alembic migration
ever adds:

- `agent_secret` (`VARCHAR(64)`)
- `enroll_code_hash` (`VARCHAR(255)`)
- `enroll_code_expires_at` (`DATETIME`)
- `override_code_hash` (`VARCHAR(255)`)

The migration chain ends at `d6e7f8a9b0c1` (overlay_forced). Only `wol_attempts/
wol_successes/wol_failures` (rev `a1bb8b056ad6`) and `overlay_forced`
(rev `d6e7f8a9b0c1`) were migrated. Every `SELECT` against `Seat` includes the
four drifted columns, so it fails even on a *present, migrated* database.

**Why the launcher DB-bootstrap flow alone would not fix it:** restoring the
latest backup, or creating a fresh DB and running `alembic upgrade head`, still
produces a schema missing those four columns. The fix requires (1) a migration
for the four columns, and (2) ensuring every DB path the launcher uses is
schema-synced.

**WAL replay trap:** deleting `arcade.db` while `arcade.db-wal` / `arcade.db-shm`
remain lets SQLite replay the WAL and resurrect the old schema. A correct
restore/create must replace all three files.

## Goal

Two coordinated changes:

- **(A) Launcher DB-bootstrap UX:** when `arcade.db` is missing at launcher
  startup, let the user choose to restore the latest backup or create a fresh
  database. When present, load it (and ensure its schema is current).
- **(B) Schema sync:** a new Alembic migration adds the four columns; the
  launcher runs `alembic upgrade head` on whatever DB it loads/restores/creates
  so present, restored, and fresh DBs all boot cleanly.

## Design

### 1. Root-cause fix — migrate the four drifted Seat columns

New Alembic migration at the current head (`d6e7f8a9b0c1` → new revision id):
add the four columns as `nullable` (purely additive, safe on a live DB).

```python
def upgrade() -> None:
    op.add_column("seats", sa.Column("agent_secret", sa.String(64), nullable=True))
    op.add_column("seats", sa.Column("enroll_code_hash", sa.String(255), nullable=True))
    op.add_column("seats", sa.Column("enroll_code_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("seats", sa.Column("override_code_hash", sa.String(255), nullable=True))
```

All four match `nullable=True` in the model, so no server_default or backfill is
required. A matching `downgrade()` drops them in reverse order.

### 2. New helper module `backend/core/db_bootstrap.py`

Pure logic, no UI (mirrors `backend/core/startup.py` / `backup_service.py`
style; unit-testable without Tkinter).

Signatures:

- `is_db_present() -> bool` — `arcade.db` exists at the same path `database.py`
  resolves (`Path(__file__).resolve().parent.parent / "arcade.db"`).
- `find_latest_backup(backup_dir: Path) -> Path | None` — newest file matching
  `arcade_*.db` (`^arcade_(\d{8}_\d{4})\.db$`), chosen by filename timestamp.
- `restore_latest_backup(backup_dir: Path) -> Path` — copies the latest backup
  to `arcade.db` **after deleting `arcade.db-wal` / `arcade.db-shm`** (temp file
  → atomic replace), then runs `alembic upgrade head` to apply any newer
  migrations. Raises if no backup exists.
- `create_fresh_database() -> None` — removes stale `arcade.db` / `-wal` / `-shm`,
  then runs `alembic upgrade head` (creates the full schema from migrations).
- `ensure_schema_current() -> None` — runs `alembic upgrade head` (idempotent;
  used on the "present DB" path as defense-in-depth).

Migrations are invoked the same way `startup.run_migrations` does (Alembic
config from `backend/alembic.ini`, `sqlalchemy.url` set to the live engine URL,
`asyncio.to_thread` to avoid the running-event-loop conflict).

### 3. Launcher integration (modal, not a new screen)

In `LauncherApp._check_and_route` (`launcher.py`), when the license is valid
**and** `arcade.config.json` exists (the path that would show `MainScreen`):

1. If DB present → `ensure_schema_current()` → proceed to `MainScreen`.
2. If DB missing → open a `CTkToplevel` modal with two buttons:
   - **Restore latest backup** — enabled only when a backup exists; label shows
     the backup's timestamp (e.g. `arcade_20260718_0300.db`).
   - **Create new database**.
   - On choice → call the matching `db_bootstrap` helper → close modal → proceed
     to `MainScreen`.
   - If the modal is closed/dismissed without a choice, cancel (stay on launcher;
     do not start with a broken or absent DB).

`backup_dir` comes from `load_config().backup_dir` (default `./backups`, project
root). Bootstrap runs only after config exists, so config is always available.

### 4. Error handling / edge cases

- **Missing DB, no backups** → modal shows only "Create new database" (Restore
  disabled).
- **Restore copy fails / corrupt backup** → error dialog, offer "Create new" as
  fallback. Atomic temp-file-then-replace so a mid-copy crash never leaves a
  corrupt `arcade.db`.
- **Server lifespan keeps `run_migrations()`** (`main.py`) as a safety net;
  bootstrap and server do not conflict (Alembic is idempotent).
- No license / no `arcade.config.json` → existing behavior (Activation / Setup
  screens); DB bootstrap is skipped (nothing to bootstrap yet).

### 5. Testing

- Unit test `test_db_bootstrap.py`:
  - `find_latest_backup` selects the newest of several `arcade_*.db` files.
  - `restore_latest_backup` copies the backup and removes `arcade.db-wal` /
    `arcade.db-shm`; the resulting `seats` table has the four new columns.
  - `create_fresh_database` produces a DB at migration head whose `seats` table
    has the four new columns.
  - `ensure_schema_current` is a no-op on an already-current DB.
- Verify the new migration applies on a DB already at `d6e7f8a9b0c1`.
- **Verification step (implementation):** confirm no other model columns are
  drifted (schema-vs-metadata check) so no other table triggers `no such
  column` after this fix.

## Out of Scope

- A full-screen `DatabaseSetupScreen` (a modal is sufficient for the binary
  choice).
- Moving migration responsibility out of the server lifespan.
- Seat/zone seeding — that remains the Setup Wizard / dashboard's job; "create
  new database" yields an empty-but-valid schema, not pre-populated seats.
- Backup *creation* / scheduling — already handled by `backup_service.py`.

## Success Criteria

1. Server boots cleanly from a present DB (migrated to head, four columns present).
2. Server boots cleanly after the launcher restores the latest backup.
3. Server boots cleanly after the launcher creates a fresh database.
4. No `no such column: seats.*` error in any of the above paths.
5. Launcher shows the choose/restore/create modal only when `arcade.db` is
   missing, and never starts the server against a broken/absent DB.
