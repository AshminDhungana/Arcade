# Default Admin + Cashier (changeable PIN in-app)

**Date:** 2026-07-18
**Status:** Approved (design)
**Component:** Backend (`backend/`), Launcher (`launcher.py`), Frontend dashboard (`frontend/`)

## 1. Problem

On a fresh setup, the login screen asks for a staff ID and PIN, but **no staff
accounts exist**, so every login fails with "Invalid staff ID or PIN".

Root cause: the launcher Setup Wizard writes credentials to
`arcade.config.json` (`admin_staff_id`, `admin_pin_hash`, `cashier_staff_id`,
`cashier_pin_hash`) but **nothing ever turns them into `Staff` rows**. Login
(`auth_service.login` → `staff_repo.get_by_id`) authenticates **only** against
the `Staff` DB table. The `Staff` table is populated in normal operation only by
the manual dev seed script (`scripts/seed_dev.py`), which is not run by the
launcher.

Additional gap: the backend already supports changing a PIN via
`PATCH /api/staff/{id}/pin` (`StaffService.update_pin`), but the dashboard's
Staff settings screen has **no UI** for it (only create / deactivate /
reactivate). So "change the PIN from the app" also needs a frontend piece.

## 2. Goal

- A default **admin** and **cashier** exist on first run so login works
  out of the box (defaults `admin`/`admin` and `cashier`/`cashier`).
- The default credentials can be **changed from within the dashboard**, not by
  editing files or env vars.
- The mechanism is robust: it works whether or not the launcher wizard ran, and
  survives restarts and a wiped DB.

## 3. Decisions (from brainstorming)

| Decision | Choice |
| --- | --- |
| Default credentials | Fixed `admin`/`admin` (and `cashier`/`cashier`); changed in-app. No `.env` needed. |
| Scope | Bootstrap **both** admin and cashier. |
| PIN-change surface | Add a **dashboard UI** (backend endpoint already exists). |
| Mechanism | **Both**: launcher wizard inserts the rows **and** server startup self-heals. |

## 4. Architecture

```
launcher.py  SetupWizard._finish()
        │  (after writing arcade.config.json)
        │  run in background thread
        ▼
   run_migrations()  +  ensure_default_staff(db)   ─┐
                                                     │  shared, single source of truth
server  lifespan  startup                           │
        │  (after _seed_legacy_secrets)             │
        ▼                                           │
   ensure_default_staff(db)  ───────────────────────┘
        │
        ▼
   Staff table: [admin (id="admin"), cashier (id="cashier")]

Login  (auth_service.login)  →  staff_repo.get_by_id  →  matches "admin"/"admin"
Dashboard Settings → Staff tab → "Change PIN" → PATCH /api/staff/{id}/pin
```

## 5. Components

### 5.1 `backend/core/bootstrap.py` (NEW)

Single idempotent coroutine:

```python
async def ensure_default_staff(db: AsyncSession) -> None:
    """Insert default admin + cashier ONLY when the staff table is empty."""
```

- Reads `get_config()`:
  - `admin_staff_id` / `admin_pin_hash`
  - `cashier_staff_id` / `cashier_pin_hash`
  - Falls back to `admin`/`admin` and `cashier`/`cashier`. If a config hash is
    missing, hash the literal default PIN with `hash_pin`.
- Creates `Staff` rows with **explicit `id`** values
  (`admin_staff_id` → `"admin"`, `cashier_staff_id` → `"cashier"`) so login with
  the human-readable ID matches `Staff.id` (the model auto-generates a UUID
  `id` by default, which would NOT match `"admin"`).
- Sets `name`, `role` (ADMIN / CASHIER), `pin_hash`, `is_active=True`,
  `token_version=0`.
- Guarded by `SELECT COUNT(*) FROM staff == 0` — never overwrites existing rows
  and never resurrects a deliberately deleted admin.

### 5.2 Server startup (`backend/main.py`)

In `lifespan`, immediately after the existing `_seed_legacy_secrets(db)` call,
add:

```python
from backend.core.bootstrap import ensure_default_staff
...
await ensure_default_staff(db)
```

Reuses the same `db` session already opened for flag loading. This is the
always-on safety net.

### 5.3 Launcher wizard (`launcher.py`)

In `SetupWizard._finish`, after writing `arcade.config.json` and before/after
routing, run a small async helper in a **background thread** so the Tkinter UI
does not freeze:

```python
await run_migrations()                        # create tables (asyncio.to_thread)
async with AsyncSessionLocal() as db:
    await ensure_default_staff(db)
    await db.commit()
```

- Wrapped in `try/except` — **non-fatal**. On any failure (missing deps,
  permissions, already-running server), log + show a brief, non-blocking
  warning. The server's startup self-heal (§5.2) still creates the accounts.
- Reuses the exact same `ensure_default_staff`, so wizard and server cannot
  drift.
- Must `load_config()` (or clear the `get_config` lru_cache) fresh after writing
  the file so the bootstrap reads the just-written values.

### 5.4 Frontend — dashboard PIN change

The backend `PATCH /api/staff/{id}/pin` (`update_staff_pin`,
`StaffService.update_pin`) already exists and increments `token_version` to
invalidate existing JWTs. The frontend only lacks the button.

- `frontend/src/api/settings.ts`:
  - `changeStaffPin(token: string | null, id: string, pin: string): Promise<Staff>`
    → `PATCH /api/staff/{id}/pin` with body `{ pin }`.
  - `useChangeStaffPin()` mutation hook (mirrors `useDeactivateStaff`).
- `frontend/src/components/settings/StaffTab.tsx`:
  - Add a **Change PIN** action per staff row (reuse existing row-action
    patterns).
  - Opens a small modal to enter the new PIN, calls the mutation, then
    invalidates the staff list query.
  - Authorization: backend enforces `require_self_or_admin`, so an admin can
    change any PIN and a staff member can change their own.

## 6. Data flow

1. Fresh setup → wizard writes `arcade.config.json` (admin/cashier defaults
   `admin`/`admin`, `cashier`/`cashier`) and seeds the `Staff` table.
2. Server boots → `ensure_default_staff` self-heals if rows are missing
   (e.g., DB wiped, or wizard seeding was skipped/failed).
3. Owner logs in with `admin` / `admin`.
4. Owner opens Settings → Staff → Change PIN → updates the admin PIN.
5. `token_version` bumps → all existing JWTs for that staff are invalidated.

## 7. Error handling

- `ensure_default_staff` is idempotent and commit-safe; if `Staff` rows already
  exist it does nothing.
- Wizard seeding failure is logged and surfaced as a non-blocking warning; the
  server self-heal covers it. Never blocks the wizard from completing.
- PIN change uses the existing validation/rate-limit/audit paths already wired
  into `auth_service` and `staff_service`.

## 8. Testing

- **Backend unit** (`backend/tests/`): `ensure_default_staff` inserts exactly
  two rows (admin, cashier) with the correct explicit `id`/`role` when the table
  is empty; a second call on a populated table inserts nothing (no duplicates).
- **Backend integration**: after bootstrap, `login("admin", "admin")` succeeds;
  `PATCH /api/staff/{id}/pin` changes the PIN and the previous JWT is rejected
  (token_version check).
- **Frontend**: unit test for `useChangeStaffPin` hook (mock the API client)
  and a component test for the Change PIN modal in `StaffTab`.
- **Manual**: fresh `launcher.py` run → complete wizard → log in with
  `admin`/`admin` → change PIN in dashboard → confirm old PIN no longer logs in.

## 9. Out of scope (YAGNI)

- Env-configurable default credentials (`.env.example`) — deferred; the chosen
  default is fixed `admin`/`admin`, changed in-app.
- Forcing a PIN change on first login, or expiry/rotation policies.
- Seed data beyond admin + cashier (members, menu, zones remain dev-seed only).

## 10. Files touched

- `backend/core/bootstrap.py` (new)
- `backend/main.py` (call `ensure_default_staff` in `lifespan`)
- `launcher.py` (`SetupWizard._finish` seeds in a background thread)
- `frontend/src/api/settings.ts` (`changeStaffPin` + hook)
- `frontend/src/components/settings/StaffTab.tsx` (Change PIN action + modal)
- `backend/tests/` (bootstrap + integration tests)
- `frontend/src/**/*.test.*` (hook / modal tests)
