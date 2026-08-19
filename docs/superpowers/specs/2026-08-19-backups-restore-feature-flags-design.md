# Section L — Backups, Restore & Feature Flags Design

**Date:** 2026-08-19
**Status:** Approved for implementation
**Related TODO items:** L.1–L.6

---

## Overview

This spec covers the remaining work for Section L of the release checklist:

- **L.1** Nightly backup with SHA256 manifest (adds integrity verification to existing backup)
- **L.2** Retention (already working, verify only)
- **L.3** Manual backup (already implemented, verify only)
- **L.4** Restore API — `POST /api/admin/restore` (new)
- **L.5** All 23 feature flags — 20 boolean + 4 config settings (add 7 new flags)
- **L.6** Daily-ops sanity after restore (new integration test)

---

## L.1 Nightly Backup with SHA256 Manifest

### Current Implementation

`backend/services/backup_service.py`:
- `run_backup()` — WAL checkpoint (`PRAGMA wal_checkpoint(TRUNCATE)`) + `shutil.copy2()` to timestamped file `arcade_YYYYMMDD_HHMM.db`
- `prune_old_backups()` — deletes files older than `backup_retain_days` (default 30), matching pattern only
- APScheduler job `_backup_job()` in `backend/core/scheduler.py` runs daily at `config.backup_time` (default `03:00`)
- Audit logging: `BACKUP_CREATED` and `BACKUP_PRUNED` via `audit_service`

### Additions

1. **Per-backup SHA256 file** (`*.db.sha256`):
   - After successful copy, compute SHA256 of the backup file
   - Write `<backup_name>.db.sha256` with format: `<hex_digest>  <filename>` (standard `sha256sum` format)
   - Example: `a1b2c3...  arcade_20260819_0300.db`

2. **manifest.json** (single file in `backup_dir`):
   - Array of objects, one per backup:
     ```json
     [
       {
         "filename": "arcade_20260819_0300.db",
         "sha256": "a1b2c3...",
         "size_bytes": 12345678,
         "created_at": "2026-08-19T03:00:00+00:00",
         "staff_id": null
       }
     ]
     ```
   - Updated atomically: write to `manifest.json.tmp`, then `os.replace()` to `manifest.json`
   - On prune: remove entries for deleted files, rewrite manifest

3. **Verification on restore**:
   - `db_bootstrap.restore_latest_backup()` (and new restore API) reads manifest, verifies SHA256 before copying
   - If mismatch: log error, skip that backup, try next newest

### Files to Modify

- `backend/services/backup_service.py` — add SHA256 computation, manifest read/write
- `backend/core/db_bootstrap.py` — add manifest verification in `restore_latest_backup()`

### Tests

- `backend/tests/test_backup.py` — add `test_run_backup_creates_sha256_and_manifest`
- `backend/tests/integration/test_ac20_backup_scheduler.py` — add `test_backup_manifest_integrity`

---

## L.2 Retention (Verify Only)

Already implemented and tested:
- `prune_old_backups()` deletes `arcade_YYYYMMDD_HHMM.db` older than `retain_days`
- Also deletes corresponding `.sha256` files
- Updates `manifest.json` atomically
- Audit `BACKUP_PRUNED` with `deleted=N`

**Verification:** Run existing tests:
- `test_backup_retention_keeps_30_days`
- `test_backup_retention_configurable`
- `test_prune_deletes_only_old_matching_files`

---

## L.3 Manual Backup (Verify Only)

Already implemented:
- `POST /api/backup/run` (Admin only) in `backend/api/routers/backup.py`
- Calls `backup_service.run_backup(db, staff_id=staff.id)`
- Returns `{backup_file, pruned_count}`
- Cashier gets 403

**Verification:** Run existing tests:
- `test_run_backup_200_for_admin`
- `test_run_backup_requires_admin`
- `test_backup_manual_trigger_endpoint`

---

## L.4 Restore API — `POST /api/admin/restore`

### Design Approach

The Launcher manages the uvicorn subprocess. The restore API coordinates with the Launcher via a signal file rather than attempting in-process restart.

### Flow

1. **Admin calls** `POST /api/admin/restore` with optional body:
   ```json
   { "backup_filename": "arcade_20260818_0300.db" }  // optional, defaults to latest
   ```

2. **Server validates**:
   - Backup file exists in `backup_dir`
   - SHA256 matches `manifest.json` entry
   - If validation fails: return `400` with detail

3. **Server writes signal file** `.restore_requested` in project root:
   ```json
   { "backup_filename": "arcade_20260818_0300.db", "requested_by": "staff_id", "requested_at": "2026-08-19T10:30:00Z" }
   ```

4. **Server returns** `202 Accepted`:
   ```json
   { "message": "Restore queued. Server will restart.", "backup_file": "arcade_20260818_0300.db" }
   ```

5. **Launcher detects signal** (poll every 5s in main loop or via IPC):
   - Reads `.restore_requested`
   - Stops uvicorn subprocess gracefully (`SIGTERM`, wait up to 10s)
   - Calls `db_bootstrap.restore_latest_backup(backup_dir)` (or specific backup)
   - Restarts uvicorn
   - Deletes `.restore_requested`

6. **Audit log**: `BACKUP_RESTORED` action with:
   - `entity_type: "backup"`
   - `entity_id: backup_filename`
   - `staff_id: admin_id`
   - `detail: "restored via API"`

### Files to Create/Modify

- **New:** `backend/api/routers/restore.py` — `POST /api/admin/restore` endpoint (Admin only)
- **Modify:** `backend/services/backup_service.py` — add `verify_backup_integrity(backup_path, manifest)` helper
- **Modify:** `backend/core/db_bootstrap.py` — add `restore_specific_backup(backup_dir, backup_filename)` variant
- **Modify:** `launcher.py` — add signal file polling in main loop, handle restore sequence

### Tests

- `backend/tests/test_restore_router.py` — new file, unit tests for restore endpoint
- `backend/tests/integration/test_ac20_backup_scheduler.py` — add `test_restore_api_validates_sha256`, `test_restore_api_returns_202`

---

## L.5 All 23 Feature Flags (20 Boolean + 4 Config)

### Current Flags (17 in `DEFAULT_FEATURE_FLAGS`)

| Flag | Type | Default | Scope |
|------|------|---------|-------|
| `enable_members` | bool | true | Members, wallet, loyalty |
| `enable_packages` | bool | true | Time bundles, passes |
| `enable_pos` | bool | true | Food/drink ordering |
| `enable_inventory` | bool | false | Stock tracking |
| `enable_reservations` | bool | true | Advance seat reservations |
| `enable_vouchers` | bool | false | Voucher generation/redemption |
| `enable_tournaments` | bool | false | Tournament/event mode |
| `enable_expense_tracking` | bool | false | Expense log, P&L |
| `enable_health_monitoring` | bool | true | PC hardware metrics |
| `require_member_for_session` | bool | false | Require member for session start |
| `enable_tuya` | bool | false | Smart plug control |
| `require_print_before_release` | bool | false | Block seat release until printed |
| `block_shift_close_unprinted` | bool | false | Block shift close if unprinted invoices |
| `shift_cash_variance_threshold` | int | 5000 | Paise threshold for shift variance flag |
| `overlay_pauses_billing` | bool | true | Pause excludes time from billing |
| `enable_assigned_time_limit` | bool | false | Hard session time limits |
| `enable_wake_on_lan` | bool | true | WoL magic packets on boot |

### New Flags (7 boolean, all default OFF)

| Flag | Type | Default | Scope |
|------|------|---------|-------|
| `enable_remote_commands` | bool | false | Remote restart/shutdown/message/screenshot (Section H) |
| `enable_analytics` | bool | false | Analytics dashboard, reports (Section K) |
| `enable_promotions` | bool | false | Promotions engine (happy hour, flash, etc.) |
| `enable_loyalty_discounts` | bool | false | Tier-based loyalty discounts at checkout (deferred F.4) |
| `enable_maintenance_mode` | bool | false | Seat maintenance mode (C.11) |
| `enable_kiosk_branding` | bool | false | Custom cafe branding on agent overlay |
| `enable_audit_export` | bool | false | Audit log export/download |

### Total: 20 boolean + 4 config = 24 settings

### Backend Changes

1. **`backend/core/bootstrap.py`** — Add 7 new flags to `DEFAULT_FEATURE_FLAGS` dict
2. **Endpoint gating** — Add `require_feature()` dependency to:
   - Remote command endpoints (H.1–H.4): `require_feature("enable_remote_commands")`
   - Analytics/reports routers (K.1–K.3): `require_feature("enable_analytics")`
   - Promotion endpoints: `require_feature("enable_promotions")`
   - Tier discount logic (when F.4 implemented): `require_feature("enable_loyalty_discounts")`
   - Maintenance endpoints (C.11): `require_feature("enable_maintenance_mode")`
   - Agent overlay branding: `require_feature("enable_kiosk_branding")`
   - Audit export endpoint (future): `require_feature("enable_audit_export")`
3. **Seed script** — `backend/scripts/seed_dev.py` already uses `DEFAULT_FEATURE_FLAGS`, no change needed

### Frontend Changes

1. **`frontend/src/api/featureFlags.ts`** — Expand `FLAG_KEYS` to include all 20 boolean flags
2. **`frontend/src/store/featureFlagStore.ts`** — `DEFAULT_FLAGS` updated with 20 keys
3. **Settings UI** — Feature Flags tab shows all 24 settings grouped:
   - **Core Features**: `enable_members`, `enable_packages`, `enable_pos`, `enable_reservations`, `enable_wake_on_lan`
   - **Operations**: `enable_inventory`, `enable_vouchers`, `enable_tournaments`, `enable_expense_tracking`, `enable_health_monitoring`, `enable_remote_commands`, `enable_analytics`, `enable_promotions`, `enable_maintenance_mode`
   - **Agent/Overlay**: `enable_tuya`, `enable_kiosk_branding`, `overlay_pauses_billing`, `require_member_for_session`, `enable_assigned_time_limit`
   - **Advanced**: `require_print_before_release`, `block_shift_close_unprinted`, `shift_cash_variance_threshold` (number), `enable_loyalty_discounts`, `enable_audit_export`
4. Boolean flags render as toggles; config settings render as number/text inputs
5. `useFeatureFlags` hook fetches all from `/api/settings` on auth

### Tests

- `backend/tests/test_feature_flags.py` — add tests for 7 new flags (cache load, refresh, require_feature 503/allow)
- `backend/tests/integration/test_ac08_feature_flags.py` — add integration tests for new flag gating
- Frontend: `featureFlagStore.test.ts` — verify all 20 boolean keys in store

---

## L.6 Daily-Ops Sanity After Restore

### Test Scenario (Integration Test)

**File:** `backend/tests/integration/test_ac20_backup_scheduler.py` — add `test_restore_daily_ops_sanity`

**Steps:**
1. Seed test data:
   - Active session on seat_1 (started 10 min ago)
   - Member with wallet balance 50000 paise
   - Open shift with cash float
   - Agent connected, sending health metrics
2. Create backup via `POST /api/backup/run` (admin)
3. Call `POST /api/admin/restore` (no body = latest)
4. Poll `/health` until server responds (max 30s)
5. Verify post-restore state:
   - Session still exists on seat_1, elapsed time ≈ original + downtime
   - Dashboard WS shows seat_1 as `IN_USE`
   - Agent re-syncs: sends `SYNC`, server adopts elapsed, no double-billing
   - Member wallet balance = 50000 paise
   - Shift still open, totals correct
   - `alembic current` shows head revision (no schema drift)

**Pass criteria:** All assertions pass, no errors in server logs.

---

## Implementation Order

1. **L.1** — SHA256 + manifest in backup_service + db_bootstrap
2. **L.4** — Restore API router + Launcher signal handling
3. **L.5** — Add 7 flags to bootstrap.py, gate endpoints, update frontend
4. **L.6** — Integration test for restore sanity
5. **L.2, L.3** — Verify existing tests pass

---

## Acceptance Criteria (from TODO.md)

| Item | Verification Command |
|------|---------------------|
| L.1 | `python -m pytest backend/tests/test_backup.py backend/tests/test_backup_router.py backend/tests/integration/test_ac20_backup_scheduler.py` |
| L.2 | Simulate 35 days; verify files >30 days auto-deleted |
| L.3 | `POST /api/admin/backup` creates backup on demand |
| L.4 | `POST /api/admin/restore` stops server, replaces DB, restarts; verify data integrity |
| L.5 | Toggle each flag in Settings/API; verify UI hides/shows, endpoints enforce guards. `python -m pytest backend/tests/test_feature_flags.py backend/tests/integration/test_ac08_feature_flags.py` |
| L.6 | After restore, verify sessions, dashboard, agent sync work. `python -m pytest backend/tests/test_bootstrap.py backend/tests/test_db_bootstrap.py` |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Restore signal file race condition | Launcher polls every 5s; signal file written atomically; server returns 202 immediately |
| SHA256 computation slow on large DB | SQLite DB typically <500MB; SHA256 takes <1s; run in backup job (already async) |
| Frontend flag list drift from backend | Single source of truth: `DEFAULT_FEATURE_FLAGS` in bootstrap.py; frontend `FLAG_KEYS` mirrors it; add test to verify parity |
| Launcher not detecting restore signal | Add IPC message from server to launcher as backup; log at each step for debugging |

---

## Migration Notes

- **No DB migration needed** — feature flags stored in `AppSettings` table, seeded on first run
- **Existing installations** — new flags default to OFF; operators enable as needed
- **Backup format compatible** — new `.sha256` and `manifest.json` are additive; old backups without hashes will be skipped on restore (fallback to next newest with valid hash)
