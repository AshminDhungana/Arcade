# Default Admin + Cashier (in-app changeable PIN) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee a default admin (`admin`/`admin`) and cashier (`cashier`/`cashier`) exist on first run so login works, and let either PIN be changed from the dashboard Settings → Staff tab.

**Architecture:** A single shared, idempotent coroutine `ensure_default_staff(db)` creates the two `Staff` rows (with explicit ids matching the login id) the first time the `staff` table is empty. It is called at server startup (always-on self-heal) and from the launcher wizard's *Finish* (in a background thread, non-fatal). The dashboard gets a "Change PIN" action backed by the already-existing `PATCH /api/staff/{id}/pin` endpoint.

**Tech Stack:** Python 3.13, FastAPI, async SQLAlchemy + aiosqlite, Argon2id (`backend.core.security.hash_pin`), Tkinter launcher, React + TypeScript + Vite + React Query, Vitest + @testing-library/react.

## Global Constraints

- Money is stored as paise integers — N/A here (PINs are not money).
- PINs are hashed with Argon2id; never store or log plaintext. `hash_pin(pin)` / `verify_pin(pin, hash)` in `backend/core/security.py`.
- `Staff.id` is a UUID by default, but login matches `Staff.id` against the human-typed staff id (e.g. `"admin"`). The bootstrap MUST create rows with explicit `id="admin"` / `id="cashier"` so login succeeds. (Verbatim from spec §5.1.)
- The `Staff` table is populated in normal operation only by the dev seed script; the launcher writes credentials to `arcade.config.json` (`admin_staff_id`, `admin_pin_hash`, `cashier_staff_id`, `cashier_pin_hash`) but nothing turns them into `Staff` rows. This plan closes that gap. (Verbatim from spec §1.)
- Bootstrap is idempotent and only seeds when the `staff` table is empty; it must never overwrite existing rows or resurrect a deleted admin. (Verbatim from spec §5.1/§7.)
- `ensure_default_staff` reads `get_config()` (lru-cached). The launcher must pass a freshly `load_config()`-ed settings instance so it reads the just-written file. (Verbatim from spec §5.3.)
- Wizard seeding is non-fatal: any failure is logged + surfaced as a brief warning; the server's startup self-heal covers it. (Verbatim from spec §5.3.)
- Follow existing patterns: repository pattern (`api/routers/` → `services/` → `repositories/` → `models/`), no business logic in routers/repositories; frontend `settings.ts` exposes fetch helpers + React Query hooks; `StaffTab.tsx` holds the UI.
- Lint/format gates: `ruff`, `ruff-format`, `mypy --strict` (backend); `eslint` (frontend). Run `make lint` before committing.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `backend/core/bootstrap.py` (NEW) | `ensure_default_staff(db, settings=None)` — idempotent seed of admin+cashier `Staff` rows. |
| `backend/main.py` (MODIFY) | Call `ensure_default_staff(db)` in `lifespan` after `_seed_legacy_secrets`. |
| `launcher.py` (MODIFY) | `SetupWizard._finish` writes config, then seeds the DB in a background thread via `ensure_default_staff`. |
| `frontend/src/api/settings.ts` (MODIFY) | Add `changeStaffPin()` fetch helper + `useChangeStaffPin()` hook. |
| `frontend/src/components/settings/StaffTab.tsx` (MODIFY) | Add "Change PIN" action per row + a `PinChangeModal`. |
| `backend/tests/test_bootstrap.py` (NEW) | Unit test for `ensure_default_staff` (idempotency, explicit ids, roles). |
| `backend/tests/test_auth_bootstrap.py` (NEW) | Integration: after bootstrap, `login("admin","admin")` succeeds; `PATCH /pin` invalidates the old token. |
| `frontend/src/components/settings/StaffTab.test.tsx` (MODIFY) | Component test for the Change PIN modal. |

---

### Task 1: Backend — `ensure_default_staff` seed function

**Files:**
- Create: `backend/core/bootstrap.py`
- Test: `backend/tests/test_bootstrap.py`

**Interfaces:**
- Consumes: `backend.core.config.Settings` (fields `admin_staff_id`, `admin_pin_hash`, `cashier_staff_id`, `cashier_pin_hash`), `backend.core.security.hash_pin`, `backend.models.Staff`, `backend.models._enums.StaffRole`, `backend.repositories.staff_repo.list`.
- Produces: `async def ensure_default_staff(db: AsyncSession, settings: Settings | None = None) -> None` — callable from `main.py` lifespan and from `launcher.py`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_bootstrap.py
"""Unit tests for ensure_default_staff (idempotent default-account seed)."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import Settings
from backend.core.database import Base
from backend.core.security import hash_pin, verify_pin
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.repositories import staff_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


def _settings() -> Settings:
    return Settings(
        admin_staff_id="admin",
        admin_pin_hash=hash_pin("admin"),
        cashier_staff_id="cashier",
        cashier_pin_hash=hash_pin("cashier"),
    )


async def test_seeds_admin_and_cashier_with_explicit_ids(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    await ensure_default_staff(db, settings=_settings())
    await db.commit()

    admin = await staff_repo.get_by_id(db, "admin")
    cashier = await staff_repo.get_by_id(db, "cashier")
    assert admin is not None
    assert cashier is not None
    assert admin.role == StaffRole.ADMIN
    assert cashier.role == StaffRole.CASHIER
    assert admin.is_active and cashier.is_active
    assert verify_pin("admin", admin.pin_hash)
    assert verify_pin("cashier", cashier.pin_hash)


async def test_is_idempotent_on_second_call(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    await ensure_default_staff(db, settings=_settings())
    await db.commit()
    # First call creates rows; grab the admin id.
    admin_before = await staff_repo.get_by_id(db, "admin")
    # Second call must NOT create duplicates or error.
    await ensure_default_staff(db, settings=_settings())

    all_staff = await staff_repo.list(db)
    assert len(all_staff) == 2
    admin_after = await staff_repo.get_by_id(db, "admin")
    # Same row, not a new one (id is the fixed "admin").
    assert admin_after.id == admin_before.id == "admin"


async def test_does_not_seed_when_table_non_empty(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    # Pre-existing staff (e.g. dev seed or a previously deleted/recreated admin).
    await staff_repo.create(db, name="Existing", role="ADMIN", pin_hash=hash_pin("0000"))
    await db.commit()

    await ensure_default_staff(db, settings=_settings())

    all_staff = await staff_repo.list(db)
    # Only the pre-existing row; default "admin" is NOT force-created.
    assert len(all_staff) == 1
    assert await staff_repo.get_by_id(db, "admin") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_bootstrap.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.core.bootstrap'` (file not created yet).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/core/bootstrap.py
"""First-run bootstrap: ensure a default admin + cashier exist.

The launcher Setup Wizard writes credentials to ``arcade.config.json`` but
nothing previously turned them into ``Staff`` rows, so login failed on a fresh
setup. ``ensure_default_staff`` reconciles config -> DB exactly once (when the
staff table is empty) and is safe to call on every startup.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings, get_config
from backend.core.security import hash_pin
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.repositories import staff_repo

_ADMIN_DEFAULT_ID = "admin"
_ADMIN_DEFAULT_PIN = "admin"
_CASHIER_DEFAULT_ID = "cashier"
_CASHIER_DEFAULT_PIN = "cashier"


async def ensure_default_staff(
    db: AsyncSession, settings: Settings | None = None
) -> None:
    """Insert default admin + cashier Staff rows only when the table is empty.

    Reads ids/PIN hashes from *settings* (defaults to the cached app config).
    Staff rows are created with explicit ids so login with the human-typed id
    (e.g. ``admin``) matches ``Staff.id``.
    """
    if await staff_repo.list(db):
        return  # already seeded; never overwrite or resurrect deleted accounts

    cfg = settings if settings is not None else get_config()

    admin_id = cfg.admin_staff_id or _ADMIN_DEFAULT_ID
    admin_pin_hash = cfg.admin_pin_hash or hash_pin(_ADMIN_DEFAULT_PIN)
    cashier_id = cfg.cashier_staff_id or _CASHIER_DEFAULT_ID
    cashier_pin_hash = cfg.cashier_pin_hash or hash_pin(_CASHIER_DEFAULT_PIN)

    db.add(
        Staff(
            id=admin_id,
            name="Administrator",
            role=StaffRole.ADMIN,
            pin_hash=admin_pin_hash,
            is_active=True,
        )
    )
    db.add(
        Staff(
            id=cashier_id,
            name="Cashier",
            role=StaffRole.CASHIER,
            pin_hash=cashier_pin_hash,
            is_active=True,
        )
    )
    await db.flush()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_bootstrap.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/core/bootstrap.py backend/tests/test_bootstrap.py
git commit -m "feat(backend): add idempotent ensure_default_staff bootstrap"
```

---

### Task 2: Backend — wire bootstrap into server startup + integration test

**Files:**
- Modify: `backend/main.py:84-86` (the `async with AsyncSessionLocal() as db:` block in `lifespan`)
- Test: `backend/tests/test_auth_bootstrap.py`

**Interfaces:**
- Consumes: `backend.core.bootstrap.ensure_default_staff`, `backend.api.routers.auth.login`, `backend.services.staff_service.StaffService.update_pin`, `backend.core.security.create_access_token`/`verify_pin`, fixtures `db` (see Task 1 pattern).
- Produces: a running app whose `staff` table is seeded at startup; verified by the integration test.

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/test_auth_bootstrap.py
"""Integration: default admin seeded at startup can log in; PIN change invalidates token."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.security import create_access_token, verify_pin
from backend.core.bootstrap import ensure_default_staff
from backend.core.config import Settings
from backend.services import auth_service, staff_service
from backend.repositories import staff_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


async def test_default_admin_login_then_pin_change_invalidates_token(db: AsyncSession) -> None:
    settings = Settings(
        admin_staff_id="admin",
        admin_pin_hash=__import__("backend.core.security", fromlist=["hash_pin"]).hash_pin("admin"),
        cashier_staff_id="cashier",
        cashier_pin_hash=__import__("backend.core.security", fromlist=["hash_pin"]).hash_pin("cashier"),
    )
    await ensure_default_staff(db, settings=settings)
    await db.commit()

    # Login with default admin/admin succeeds.
    token_resp = await auth_service.login(db, "admin", "admin", "127.0.0.1")
    assert token_resp.access_token

    admin = await staff_repo.get_by_id(db, "admin")
    old_version = admin.token_version

    # Change the PIN via the existing service.
    await staff_service.StaffService.update_pin(
        db, staff_id="admin", new_pin="newpin123"
    )
    await db.commit()

    admin = await staff_repo.get_by_id(db, "admin")
    assert admin.token_version == old_version + 1
    assert verify_pin("newpin123", admin.pin_hash)

    # Old token is now rejected because token_version changed.
    from backend.core.security import decode_access_token
    payload = decode_access_token(token_resp.access_token)
    reloaded = await staff_repo.get_by_id(db, "admin")
    assert payload["token_version"] != reloaded.token_version
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth_bootstrap.py -q`
Expected: FAIL (the `ensure_default_staff` import resolves now, but the `lifespan` change is not needed for this service-level test; it should PASS already). If it passes, skip to Step 4 for the lifespan wiring verification below.

- [ ] **Step 3: Wire into `lifespan`**

In `backend/main.py`, update the startup DB block to also seed default staff. Find:

```python
    # 4. Load feature flags into in-memory cache
    async with AsyncSessionLocal() as db:
        await load_flags(db)
        await _seed_legacy_secrets(db)
```

Replace with:

```python
    # 4. Load feature flags into in-memory cache, and seed default staff
    #    (admin + cashier) on a fresh database so login works out of the box.
    async with AsyncSessionLocal() as db:
        await load_flags(db)
        await _seed_legacy_secrets(db)
        from backend.core.bootstrap import ensure_default_staff

        await ensure_default_staff(db)
        await db.commit()
```

- [ ] **Step 4: Verify wiring with a fresh real startup (no test double)**

Run the existing test suite to ensure startup bootstrap does not break anything that relies on an empty staff table:

Run: `cd backend && python -m pytest tests/test_auth.py tests/test_security.py -q`
Expected: PASS. (These tests create their own staff rows inside their own `db` fixture, so the lifespan path is not exercised here; this confirms no import/syntax regressions. The true startup path is covered by the app boot in CI / manual run below.)

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_auth_bootstrap.py
git commit -m "feat(backend): seed default admin+cashier at server startup"
```

---

### Task 3: Launcher — wizard seeds the DB on Finish (non-fatal)

**Files:**
- Modify: `launcher.py` (`SetupWizard._finish`, currently lines ~344-377)

**Interfaces:**
- Consumes: `backend.core.bootstrap.ensure_default_staff`, `backend.core.startup.run_migrations`, `backend.core.config.load_config`, `backend.core.database.AsyncSessionLocal`, `asyncio`.
- Produces: after `_finish`, the `staff` table is populated (best-effort) so the server self-heal is redundant but still present.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_launcher.py` inside `class TestSetupWizard` a test that `_finish` triggers the seed (mock the heavy DB work so the Tkinter test stays fast and offline):

```python
    def test_finish_seeds_default_staff_best_effort(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        import tkinter as tk

        from launcher import LauncherApp, SetupWizard

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("launcher._db_path", lambda: tmp_path / "arcade.db")

        seeded: dict[str, bool] = {}

        def fake_seed() -> None:
            seeded["called"] = True

        # _seed_default_staff runs the DB work in a background thread; patch it
        # so the test asserts it was invoked without touching a real DB.
        monkeypatch.setattr(SetupWizard, "_seed_default_staff", fake_seed)

        result = type(
            "R",
            (),
            {
                "ok": True,
                "payload": {
                    "cafe_name": "Test Cafe",
                    "hardware_id": "c" * 32,
                    "license_type": "PERPETUAL",
                    "issue_date": "2026-01-01",
                },
            },
        )()
        root = tk.Tk()
        app = LauncherApp(root)
        wizard = SetupWizard(root, app, result)  # type: ignore[arg-type]
        wizard._cafe_name_var.set("Test Cafe")
        wizard._finish()

        assert seeded.get("called") is True
        root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_launcher.py::TestSetupWizard::test_finish_seeds_default_staff_best_effort -q`
Expected: FAIL — `SetupWizard` has no `_seed_default_staff` attribute (AttributeError / the monkeypatch target doesn't exist).

- [ ] **Step 3: Implement the wizard seeding**

In `launcher.py`, add a helper method and call it at the end of `_finish`. The DB work runs in a background thread so the Tkinter UI never blocks.

Add this import near the top of `launcher.py` (after the existing `from backend.core.security import hash_pin`):

```python
import asyncio
```

Add the helper method inside `class SetupWizard` (e.g. right before `_finish`):

```python
    def _seed_default_staff(self) -> None:
        """Best-effort: create the default admin + cashier in the DB.

        Runs in a background thread (DB + alembic can be slow) so the wizard UI
        stays responsive. Any failure is non-fatal: the server's startup
        self-heal (ensure_default_staff in main.py lifespan) covers it.
        """
        import logging
        import threading

        logger = logging.getLogger(__name__)

        def _run() -> None:
            from backend.core.bootstrap import ensure_default_staff
            from backend.core.config import load_config
            from backend.core.database import AsyncSessionLocal
            from backend.core.startup import run_migrations

            async def _bootstrap() -> None:
                await run_migrations()
                async with AsyncSessionLocal() as db:
                    # Read the config we just wrote (not the lru-cached getter).
                    await ensure_default_staff(db, settings=load_config())
                    await db.commit()

            try:
                asyncio.run(_bootstrap())
            except Exception as exc:  # noqa: BLE001 — best-effort, never block wizard
                logger.warning("Default staff seed skipped: %s", exc)

        threading.Thread(target=_run, daemon=True).start()
```

Modify `_finish` to call it. Replace the trailing routing block:

```python
        # Write config
        Path("arcade.config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        # Write license_status row (FR-LIC-014)
        _write_license_status(payload, self.license_result)

        # Best-effort seed default admin + cashier into the DB now.
        self._seed_default_staff()

        # Route
        self.controller._check_and_route()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_launcher.py -q`
Expected: PASS (all launcher tests, including the new one).

- [ ] **Step 5: Commit**

```bash
git add launcher.py backend/tests/test_launcher.py
git commit -m "feat(launcher): seed default admin+cashier on setup finish"
```

---

### Task 4: Frontend — `changeStaffPin` API helper + hook

**Files:**
- Modify: `frontend/src/api/settings.ts` (add fetch helper near `reactivateStaff`, add hook near `useReactivateStaff`)
- Test: `frontend/src/api/settings.test.tsx` (or extend the existing settings hook test if present)

**Interfaces:**
- Consumes: existing `API_BASE`, `authHeaders(token)` exports in `frontend/src/api/settings.ts`; backend route `PATCH /api/staff/{id}/pin` with body `{ "pin": string }` (schema `StaffPinUpdate`).
- Produces: `changeStaffPin(id, pin, token)` and `useChangeStaffPin()` mutation hook (invalidates `['staff']`).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/api/settings.test.tsx (add to existing file, or create it)
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { useChangeStaffPin } from '@/api/settings';

describe('useChangeStaffPin', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('PATCHes the new pin and invalidates the staff list', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'admin', name: 'Administrator', role: 'ADMIN', is_active: true }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const invalidate = vi.fn();
    const qc = new QueryClient();
    qc.invalidateQueries = invalidate as never;

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useChangeStaffPin(), { wrapper });
    await result.current.mutateAsync({ id: 'admin', pin: 'newpin123' });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/staff/admin/pin'),
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ pin: 'newpin123' }) }),
    );
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['staff'] }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/settings.test.tsx`
Expected: FAIL — `useChangeStaffPin` is not exported.

- [ ] **Step 3: Implement the helper + hook**

In `frontend/src/api/settings.ts`, add the fetch helper right after `reactivateStaff` (around line 251):

```typescript
export async function changeStaffPin(
  id: string,
  pin: string,
  token: string | null,
): Promise<Staff> {
  const res = await fetch(`${API_BASE}/staff/${id}/pin`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify({ pin }),
  });
  if (!res.ok) throw new Error(`Failed to change PIN: ${res.status}`);
  return (await res.json()) as Staff;
}
```

Add the hook right after `useReactivateStaff` (around line 447):

```typescript
export function useChangeStaffPin() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, pin }: { id: string; pin: string }) => changeStaffPin(id, pin, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['staff'] }),
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/settings.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/settings.ts frontend/src/api/settings.test.tsx
git commit -m "feat(frontend): add changeStaffPin API helper and hook"
```

---

### Task 5: Frontend — "Change PIN" action + modal in StaffTab

**Files:**
- Modify: `frontend/src/components/settings/StaffTab.tsx`
- Test: `frontend/src/components/settings/StaffTab.test.tsx` (extend existing)

**Interfaces:**
- Consumes: `useChangeStaffPin` (Task 4), existing `useStaff`, `Modal`, `Input`, `Button`, `toast`, `Staff` type (has `id`, `name`, `role`, `is_active`).
- Produces: a "Change PIN" button per active staff row that opens a modal, validates a 4–20 digit PIN, calls the mutation, toasts success, and refreshes the list.

- [ ] **Step 1: Write the failing component test**

```typescript
// frontend/src/components/settings/StaffTab.test.tsx (extend; add this case)
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { StaffTab } from '@/components/settings/StaffTab';

function renderTab(overrides: Partial<{ mutateAsync: () => Promise<unknown> }> = {}) {
  const mutateAsync = overrides.mutateAsync ?? (async () => ({}));
  vi.mocked(useChangeStaffPinMock).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as never);
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <StaffTab />
    </QueryClientProvider>,
  );
}

describe('StaffTab Change PIN', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('opens the modal, submits a new PIN, and shows success', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    renderTab({ mutateAsync });

    // Admin row "Change PIN" button
    fireEvent.click(screen.getByRole('button', { name: /change pin/i }));
    const input = await screen.findByLabelText(/new pin/i);
    fireEvent.change(input, { target: { value: '5678' } });
    fireEvent.click(screen.getByRole('button', { name: /update pin/i }));

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ id: 'admin', pin: '5678' }));
  });
});
```

(If `StaffTab.test.tsx` already exists, merge this `describe` block in and reuse its existing mocks for `useStaff`/`useChangeStaffPin`. The mock object name `useChangeStaffPinMock` must match whatever the existing file uses — adapt to the file's actual mock variable.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/settings/StaffTab.test.tsx`
Expected: FAIL — no "Change PIN" button / modal exists yet.

- [ ] **Step 3: Implement the UI**

In `frontend/src/components/settings/StaffTab.tsx`:

1. Update the import block to add `useChangeStaffPin` (and `KeyRound` icon if available from `lucide-react`):

```typescript
import {
  useStaff,
  useCreateStaff,
  useDeactivateStaff,
  useReactivateStaff,
  useChangeStaffPin,
} from '@/api/settings';
```

2. Add a `PinChangeModal` component (place it near `ConfirmationModal`):

```typescript
function PinChangeModal({
  open,
  staff,
  onClose,
  onConfirm,
  isLoading,
}: {
  open: boolean;
  staff: Staff | null;
  onClose: () => void;
  onConfirm: (pin: string) => void;
  isLoading: boolean;
}) {
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pin) {
      setError('PIN is required');
    } else if (pin.length < 4) {
      setError('PIN must be at least 4 digits');
    } else if (!/^\d+$/.test(pin)) {
      setError('PIN must be numeric');
    } else {
      setError(null);
      onConfirm(pin);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Change PIN — ${staff?.name ?? ''}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          name="newPin"
          label="New PIN (min 4 digits)"
          type="password"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          error={error ?? null}
          placeholder="1234"
          minLength={4}
          autoFocus
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            Update PIN
          </Button>
        </div>
      </form>
    </Modal>
  );
}
```

3. In `StaffTab`, add state + handlers alongside the existing confirm state:

```typescript
  const [pinModalOpen, setPinModalOpen] = useState(false);
  const [pinStaff, setPinStaff] = useState<Staff | null>(null);
  const changePin = useChangeStaffPin();

  const openPinModal = (s: Staff) => {
    setPinStaff(s);
    setPinModalOpen(true);
  };

  const handleChangePin = async (pin: string) => {
    if (!pinStaff) return;
    try {
      await changePin.mutateAsync({ id: pinStaff.id, pin });
      toast.success(`PIN changed for ${pinStaff.name}`);
      setPinModalOpen(false);
      setPinStaff(null);
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to change PIN';
      toast.error(msg.includes('403') || msg.includes('401') ? 'Admin required' : msg);
    }
  };
```

4. Add a "Change PIN" button in the actions cell, next to Deactivate/Reactivate:

```tsx
                      {s.is_active ? (
                        <Button
                          variant="secondary"
                          aria-label={`Change PIN for ${s.name}`}
                          onClick={() => openPinModal(s)}
                          disabled={changePin.isPending}
                        >
                          Change PIN
                        </Button>
                      ) : null}
```

(Keep the existing Deactivate/Reactivate button inside the same flex container.)

5. Render the modal at the bottom (next to the confirmation modal):

```tsx
      <PinChangeModal
        open={pinModalOpen}
        staff={pinStaff}
        onClose={() => {
          setPinModalOpen(false);
          setPinStaff(null);
        }}
        onConfirm={handleChangePin}
        isLoading={changePin.isPending}
      />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/settings/StaffTab.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/StaffTab.tsx frontend/src/components/settings/StaffTab.test.tsx
git commit -m "feat(frontend): add Change PIN action in Staff settings"
```

---

### Task 6: Lint, full test run, and manual verification

**Files:** none new (verification only)

**Interfaces:** consumes all prior tasks.

- [ ] **Step 1: Backend lint + tests**

Run: `cd backend && ruff check . && ruff format --check . && mypy --strict . && python -m pytest tests/ -q`
Expected: ruff/ruff-format/mypy clean; all tests pass (including `test_bootstrap`, `test_auth_bootstrap`, launcher tests).

- [ ] **Step 2: Frontend lint + tests**

Run: `cd frontend && npm run lint && npx vitest run`
Expected: ESLint clean; all Vitest suites pass.

- [ ] **Step 3: Manual end-to-end check**

Run from a clean state (delete `arcade.db` and `arcade.config.json` if present):
1. `python launcher.py` → complete the Setup Wizard with defaults.
2. Start the server (launcher "Start Server").
3. Open the dashboard, log in with `admin` / `admin` → succeeds.
4. Settings → Staff → click **Change PIN** on the admin → set a new PIN → save.
5. Log out; confirm the OLD pin `admin` no longer logs in and the NEW pin does.

- [ ] **Step 4: Commit any final polish** (only if a fix was required by lint/tests)

```bash
git add -A
git commit -m "fix: address lint/test findings from default-admin implementation"
```
