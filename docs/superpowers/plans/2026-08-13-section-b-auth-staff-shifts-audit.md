# Section B (Auth, Staff, Shifts & Audit) Gap-Closing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three Section B gaps — frontend shift UI, audit gaps (settings changes + license check), and the `shift_cash_variance_threshold` — then verify checklist items B.1–B.9.

**Architecture:** Backend keeps its service/router/repository layering: live shift totals are computed by a shared helper in `shift_service` and returned by extending `GET /api/shifts/current`; the variance threshold is an `AppSettings` row (seeded default 5000 paise); audit gaps are closed by logging `SETTINGS_CHANGED` in the settings router and by a new admin-only license router. Frontend follows the existing `analytics.ts` API-client pattern and the `ui/Modal` component pattern.

**Tech Stack:** FastAPI + SQLAlchemy async + aiosqlite (backend); React + TanStack Query + Vite + Vitest (frontend); Argon2id via passlib; pytest with ASGITransport + dependency overrides.

**Spec:** `docs/superpowers/specs/2026-08-13-section-b-auth-staff-shifts-audit-design.md` (approved).

## Global Constraints

- Money is integer paise everywhere (backend paise, frontend ₹ input converted with `Math.round(amount * 100)`).
- No comments unless they explain a non-obvious why (house style: docstrings on modules/functions, brief inline comments allowed).
- Audit entries go through `backend.services.audit_service.log` with `staff_id`, `entity_type`, `entity_id`, `detail` populated.
- All new audit actions must be `AuditAction` enum members; new settings must go through `DEFAULT_FEATURE_FLAGS` in `backend/core/bootstrap.py` (single source of truth; `backend/scripts/seed_dev.py` re-exports it).
- Role gates use `backend.api.deps.require_admin` / `require_cashier`.
- Frontend monetary display uses `formatPaise` from `@/hooks/useFormatPaise`.
- Tests: backend `pytest` (async, ASGITransport + dependency overrides; never hit a real arcade.db); frontend `vitest` with `vi.mock` on the API layer.
- Lint must pass after each task: `make lint` (ruff + mypy strict + ESLint).
- Verify checklist items with the exact commands from the spec; fix failures via reproduce → minimal fix → regression test → verify → record.

---

## File Structure

**Backend — create:**
- `backend/api/routers/license.py` — admin-only `POST /api/license/verify` + audit.
- `backend/tests/test_license_router.py` — license endpoint role gate + audit tests.
- `backend/tests/test_pin_hashing.py` — B.2 Argon2id verification.
- `backend/tests/test_permissions_matrix.py` — B.4 cashier 403 matrix.
- `backend/tests/test_audit_completeness.py` — B.8 audit completeness run.

**Backend — modify:**
- `backend/schemas/shift.py` — add `ShiftCurrentResponse`; add `variance_flagged` to `ShiftReportResponse`.
- `backend/services/shift_service.py` — `_compute_live_totals` helper, `get_current_shift_totals`, threshold read, `SHIFT_VARIANCE` audit on flagged close.
- `backend/api/routers/shifts.py` — `GET /current` returns `ShiftCurrentResponse | None`.
- `backend/core/bootstrap.py` — seed `shift_cash_variance_threshold`.
- `backend/models/_enums.py` — `AuditAction.SHIFT_VARIANCE`, `AuditAction.LICENSE_CHECK`.
- `backend/api/routers/settings.py` — audit `SETTINGS_CHANGED`.
- `backend/api/routers/__init__.py` — register `license_router`.
- `backend/tests/test_shift_service.py` — live-totals + threshold tests.
- `backend/tests/test_shifts_router.py` — current-shift shape update.
- `backend/tests/test_settings_patch.py` — settings audit test.
- `backend/tests/integration/test_ac12_license_verification.py` — replace skipped endpoint test.

**Frontend — create:**
- `frontend/src/types/shift.ts` — `ShiftResponse`, `ShiftCurrentResponse`.
- `frontend/src/api/shifts.ts` — client + hooks.
- `frontend/src/api/__tests__/shiftsApi.test.ts` — client tests.
- `frontend/src/components/ShiftModal.tsx` — the shift UI.
- `frontend/src/components/__tests__/ShiftModal.test.tsx` — component tests.

**Frontend — modify:**
- `frontend/src/pages/Dashboard.tsx` — Shift button + modal wiring.
- `frontend/src/pages/Dashboard.test.tsx` — button presence test.

**Docs — modify:**
- `docs/TODO.md` — mark B.1–B.9 complete.

---

### Task 1: Shift live totals (backend)

**Files:**
- Modify: `backend/schemas/shift.py`
- Modify: `backend/services/shift_service.py`
- Modify: `backend/api/routers/shifts.py`
- Test: `backend/tests/test_shift_service.py`
- Test: `backend/tests/test_shifts_router.py`

**Interfaces:**
- Produces: `backend.services.shift_service.get_current_shift_totals(db: AsyncSession) -> ShiftCurrentResponse | None` — used by the router; `ShiftCurrentResponse` has `shift: ShiftResponse`, `session_count: int`, `total_revenue_paise: int`, `average_duration_seconds: float`, `expected_cash_paise: int`.
- Produces: `backend.services.shift_service._compute_live_totals(db, shift) -> ShiftLiveTotals` — private dataclass (`session_count`, `invoice_count`, `total_revenue_paise`, `pos_total_paise`, `expected_cash_paise`, `average_duration_seconds`); Task 2 reuses it in `close_shift` and the report.

- [ ] **Step 1: Add the failing schema test**

Add to `backend/tests/test_shift_service.py` imports:

```python
from backend.models._enums import (
    AuditAction,
    InvoicePrintStatus,
    PaymentMethod,
    PricingModel,
    SessionStatus,
    ShiftStatus,
)
from backend.services.shift_service import (
    close_shift,
    get_current_shift,
    get_current_shift_totals,
    get_shift_report,
    open_shift,
)
```

Append these tests:

```python
async def test_get_current_shift_totals_live_values(db: AsyncSession) -> None:
    """B.5: revenue, sessions, avg duration, expected cash for the open shift."""
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)

    finished = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )
    finished.status = SessionStatus.COMPLETED
    finished.started_at = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    finished.ended_at = datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    finished.total_paused_seconds = 300
    await session_repo.update(db, finished)
    await invoice_repo.create(
        db,
        session_id=finished.id,
        shift_id=shift.id,
        payment_method=PaymentMethod.CASH,
        total_paise=1500,
        pos_total_paise=300,
    )
    # In-progress session counts toward session_count but not the average.
    await session_repo.create(
        db,
        seat_id="seat-2",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )

    current = await get_current_shift_totals(db)
    assert current is not None
    assert current.shift.id == shift.id
    assert current.shift.float_paise == 5000
    assert current.session_count == 2
    assert current.total_revenue_paise == 1500
    assert current.expected_cash_paise == 6500  # float 5000 + cash 1500
    # 1 hour minus 300s paused = 3300s
    assert current.average_duration_seconds == pytest.approx(3300.0)


async def test_get_current_shift_totals_none_when_no_shift_open(
    db: AsyncSession,
) -> None:
    assert await get_current_shift_totals(db) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_shift_service.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_current_shift_totals'`.

- [ ] **Step 3: Add the schema**

Add to `backend/schemas/shift.py` after `ShiftReportResponse`:

```python
class ShiftCurrentResponse(BaseResponseSchema):
    shift: ShiftResponse
    session_count: int
    total_revenue_paise: int
    average_duration_seconds: float
    expected_cash_paise: int
```

- [ ] **Step 4: Implement the service helper + current-totals function**

In `backend/services/shift_service.py`:

1. Extend the enum import to include `SessionStatus`:

```python
from backend.models._enums import (
    AuditAction,
    InvoicePrintStatus,
    PaymentMethod,
    SessionStatus,
    ShiftStatus,
)
```

2. Extend the schema import:

```python
from backend.schemas.shift import (
    ShiftCurrentResponse,
    ShiftReportResponse,
    ShiftResponse,
)
```

3. Add the dataclass + helper + public function after the `ShiftReport` dataclass:

```python
@dataclass(frozen=True)
class ShiftLiveTotals:
    session_count: int
    invoice_count: int
    total_revenue_paise: int
    pos_total_paise: int
    expected_cash_paise: int
    average_duration_seconds: float


async def _compute_live_totals(db: AsyncSession, shift: Shift) -> ShiftLiveTotals:
    """Shared reconciliation math for live totals and the close report."""
    sessions = await session_repo.list_by_shift(db, shift.id)
    invoices = await invoice_repo.list_by_shift(db, shift.id)

    cash_collected_paise = sum(
        i.total_paise for i in invoices if i.payment_method == PaymentMethod.CASH
    )
    total_revenue_paise = sum(i.total_paise for i in invoices)
    pos_total_paise = sum(i.pos_total_paise for i in invoices)

    completed = [
        s for s in sessions if s.status == SessionStatus.COMPLETED and s.ended_at is not None
    ]
    if completed:
        total = 0.0
        for s in completed:
            total += (s.ended_at - s.started_at).total_seconds() - s.total_paused_seconds
        average_duration_seconds = total / len(completed)
    else:
        average_duration_seconds = 0.0

    return ShiftLiveTotals(
        session_count=len(sessions),
        invoice_count=len(invoices),
        total_revenue_paise=total_revenue_paise,
        pos_total_paise=pos_total_paise,
        expected_cash_paise=shift.float_paise + cash_collected_paise,
        average_duration_seconds=average_duration_seconds,
    )


async def get_current_shift_totals(db: AsyncSession) -> ShiftCurrentResponse | None:
    """Live shift-scoped totals for the currently OPEN shift, or ``None``."""
    shift = await shift_repo.get_open_shift(db)
    if shift is None:
        return None
    _attach_utc(shift)
    totals = await _compute_live_totals(db, shift)
    return ShiftCurrentResponse(
        shift=ShiftResponse.model_validate(shift),
        session_count=totals.session_count,
        total_revenue_paise=totals.total_revenue_paise,
        average_duration_seconds=totals.average_duration_seconds,
        expected_cash_paise=totals.expected_cash_paise,
    )
```

- [ ] **Step 5: Refactor `get_shift_report` to reuse the helper**

Replace the body of `get_shift_report` (the whole function) with:

```python
async def get_shift_report(db: AsyncSession, *, shift_id: str) -> ShiftReportResponse:
    """Build a cash-reconciliation report for *shift_id*.

    expected_cash = float_paise + sum(invoice.total_paise where
    payment_method == CASH). variance = counted_paise - expected_cash
    (``None`` while the shift is still open).
    """
    shift = await shift_repo.get_by_id(db, shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")

    totals = await _compute_live_totals(db, shift)
    _attach_utc(shift)

    variance_paise = (
        shift.counted_paise - totals.expected_cash_paise
        if shift.counted_paise is not None
        else None
    )
    report = ShiftReport(
        shift=shift,
        session_count=totals.session_count,
        invoice_count=totals.invoice_count,
        total_revenue_paise=totals.total_revenue_paise,
        pos_total_paise=totals.pos_total_paise,
        cash_collected_paise=totals.expected_cash_paise - shift.float_paise,
        expected_cash_paise=totals.expected_cash_paise,
        variance_paise=variance_paise,
    )
    return ShiftReportResponse(
        shift=ShiftResponse.model_validate(report.shift),
        session_count=report.session_count,
        invoice_count=report.invoice_count,
        total_revenue_paise=report.total_revenue_paise,
        pos_total_paise=report.pos_total_paise,
        cash_collected_paise=report.cash_collected_paise,
        expected_cash_paise=report.expected_cash_paise,
        variance_paise=report.variance_paise,
    )
```

- [ ] **Step 6: Update the router**

In `backend/api/routers/shifts.py`, replace the `GET /current` handler and extend the schema import:

```python
from backend.schemas.shift import (
    ShiftCloseRequest,
    ShiftCurrentResponse,
    ShiftOpenRequest,
    ShiftReportResponse,
    ShiftResponse,
)
```

```python
@router.get("/current", response_model=ShiftCurrentResponse | None)
async def get_current_shift(db: DbDep, staff: CashierDep) -> ShiftCurrentResponse | None:
    return await shift_service.get_current_shift_totals(db)
```

- [ ] **Step 7: Update the router test**

In `backend/tests/test_shifts_router.py`, replace `test_get_current_returns_open` with:

```python
async def test_get_current_returns_open_with_totals(cashier_client: AsyncClient) -> None:
    await cashier_client.post("/api/shifts/open", json={"float_paise": 5000})
    resp = await cashier_client.get("/api/shifts/current")
    assert resp.status_code == 200
    body = resp.json()
    assert body["shift"]["status"] == "OPEN"
    assert body["shift"]["float_paise"] == 5000
    assert body["session_count"] == 0
    assert body["total_revenue_paise"] == 0
    assert body["average_duration_seconds"] == 0.0
    assert body["expected_cash_paise"] == 5000


async def test_get_current_returns_null_when_no_shift(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.get("/api/shifts/current")
    assert resp.status_code == 200
    assert resp.json() is None
```

- [ ] **Step 8: Run the full test batch**

Run: `python -m pytest backend/tests/test_shift_service.py backend/tests/test_shifts_router.py -v`
Expected: all PASS (existing report tests still pass — additive refactor).

- [ ] **Step 9: Lint and commit**

Run: `make lint`
Expected: clean (ruff + mypy strict).

```bash
git add backend/schemas/shift.py backend/services/shift_service.py backend/api/routers/shifts.py backend/tests/test_shift_service.py backend/tests/test_shifts_router.py
git commit -m "feat(shifts): live current-shift totals in GET /api/shifts/current"
```

---

### Task 2: Variance threshold + flagged-close audit (backend)

**Files:**
- Modify: `backend/core/bootstrap.py` (seed `shift_cash_variance_threshold`)
- Modify: `backend/models/_enums.py` (`AuditAction.SHIFT_VARIANCE`)
- Modify: `backend/schemas/shift.py` (`variance_flagged` on `ShiftReportResponse`)
- Modify: `backend/services/shift_service.py` (threshold read + report flag + close audit)
- Test: `backend/tests/test_shift_service.py`

**Interfaces:**
- Consumes: `_compute_live_totals(db, shift)` from Task 1.
- Produces: `_read_variance_threshold(db: AsyncSession) -> int` (reads `AppSettings` row `shift_cash_variance_threshold`, default 5000); `variance_flagged: bool` on `ShiftReportResponse`; `AuditAction.SHIFT_VARIANCE` logged in `close_shift` when `abs(variance) > threshold`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_shift_service.py`:

```python
async def _set_threshold(db: AsyncSession, paise: str) -> None:
    from backend.models.settings import AppSettings

    db.add(AppSettings(key="shift_cash_variance_threshold", value=paise))
    await db.flush()


def test_shift_variance_audit_action_defined() -> None:
    assert AuditAction.SHIFT_VARIANCE.value == "SHIFT_VARIANCE"


def test_shift_variance_threshold_seeded_default() -> None:
    from backend.core.bootstrap import DEFAULT_FEATURE_FLAGS

    assert DEFAULT_FEATURE_FLAGS["shift_cash_variance_threshold"] == "5000"


async def test_close_shift_audits_variance_over_threshold(db: AsyncSession) -> None:
    await _set_threshold(db, "100")
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    sess = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )
    await invoice_repo.create(
        db,
        session_id=sess.id,
        shift_id=shift.id,
        payment_method=PaymentMethod.CASH,
        total_paise=1500,
    )
    # expected = 6500, counted = 6800 -> variance +300 > 100 -> flagged
    await close_shift(db, staff_id="staff-1", closing_cash_paise=6800)
    logs = await audit_repo.list(db, action=AuditAction.SHIFT_VARIANCE.value)
    assert len(logs) == 1
    assert "variance_paise=300" in logs[0].detail
    assert "threshold_paise=100" in logs[0].detail


async def test_close_shift_no_variance_audit_within_threshold(db: AsyncSession) -> None:
    await _set_threshold(db, "100")
    await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    # variance = +50 <= 100 -> not flagged
    await close_shift(db, staff_id="staff-1", closing_cash_paise=5050)
    logs = await audit_repo.list(db, action=AuditAction.SHIFT_VARIANCE.value)
    assert logs == []


async def test_close_shift_no_variance_audit_without_threshold_row(db: AsyncSession) -> None:
    """Default threshold 5000 applies when no setting row exists."""
    await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    # variance = +1000 <= 5000 -> not flagged
    await close_shift(db, staff_id="staff-1", closing_cash_paise=6000)
    logs = await audit_repo.list(db, action=AuditAction.SHIFT_VARIANCE.value)
    assert logs == []


async def test_get_shift_report_variance_flagged_when_over_threshold(
    db: AsyncSession,
) -> None:
    await _set_threshold(db, "100")
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    sess = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )
    await invoice_repo.create(
        db,
        session_id=sess.id,
        shift_id=shift.id,
        payment_method=PaymentMethod.CASH,
        total_paise=1500,
    )
    await close_shift(db, staff_id="staff-1", closing_cash_paise=6800)
    report = await get_shift_report(db, shift_id=shift.id)
    assert report.variance_paise == 300
    assert report.variance_flagged is True


async def test_get_shift_report_not_flagged_within_threshold(db: AsyncSession) -> None:
    await _set_threshold(db, "100")
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    await close_shift(db, staff_id="staff-1", closing_cash_paise=5050)
    report = await get_shift_report(db, shift_id=shift.id)
    assert report.variance_paise == 50
    assert report.variance_flagged is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_shift_service.py -v`
Expected: FAIL — `SHIFT_VARIANCE` enum missing, `shift_cash_variance_threshold` key missing, `variance_flagged` attribute missing on report.

- [ ] **Step 3: Add the enum member**

In `backend/models/_enums.py`, add next to `SHIFT_CLOSE_UNPRINTED`:

```python
    SHIFT_VARIANCE = "SHIFT_VARIANCE"
```

- [ ] **Step 4: Seed the setting**

In `backend/core/bootstrap.py`, add to `DEFAULT_FEATURE_FLAGS` after `"block_shift_close_unprinted"`:

```python
    "shift_cash_variance_threshold": "5000",
```

- [ ] **Step 5: Add `variance_flagged` to the report schema**

In `backend/schemas/shift.py`, change `ShiftReportResponse` to:

```python
class ShiftReportResponse(BaseResponseSchema):
    shift: ShiftResponse
    session_count: int
    invoice_count: int
    total_revenue_paise: int
    pos_total_paise: int
    cash_collected_paise: int
    expected_cash_paise: int
    variance_paise: int | None = None
    variance_flagged: bool = False
```

- [ ] **Step 6: Implement threshold read + flag + close audit in the service**

In `backend/services/shift_service.py`:

1. Add the import after the existing `from backend.models._enums import (...)` block:

```python
from backend.models.settings import AppSettings
```

2. Add constants + reader after `_BLOCK_SHIFT_CLOSE_FLAG`:

```python
_VARIANCE_THRESHOLD_KEY = "shift_cash_variance_threshold"
_DEFAULT_VARIANCE_THRESHOLD_PAISE = 5000


async def _read_variance_threshold(db: AsyncSession) -> int:
    """Read the admin-editable variance threshold (paise); 5000 when unset/bad."""
    row = await db.get(AppSettings, _VARIANCE_THRESHOLD_KEY)
    if row is None:
        return _DEFAULT_VARIANCE_THRESHOLD_PAISE
    try:
        return int(row.value)
    except ValueError:
        return _DEFAULT_VARIANCE_THRESHOLD_PAISE
```

3. In `close_shift`, after the `SHIFT_CLOSE` audit log (after the `detail=f"counted_paise={closing_cash_paise}"` block), add:

```python
    totals = await _compute_live_totals(db, shift)
    variance = closing_cash_paise - totals.expected_cash_paise
    threshold = await _read_variance_threshold(db)
    if abs(variance) > threshold:
        await audit_service.log(
            db,
            action=AuditAction.SHIFT_VARIANCE,
            entity_type="shift",
            entity_id=shift.id,
            staff_id=staff_id,
            detail=f"variance_paise={variance};threshold_paise={threshold}",
        )
```

4. In `get_shift_report`, after `_attach_utc(shift)`, add:

```python
    threshold = await _read_variance_threshold(db)
    variance_flagged = variance_paise is not None and abs(variance_paise) > threshold
```

and add `variance_flagged=variance_flagged,` to the returned `ShiftReportResponse(...)`.

- [ ] **Step 7: Run the test batch**

Run: `python -m pytest backend/tests/test_shift_service.py backend/tests/test_shifts_router.py backend/tests/integration/test_ac10_shift_reconciliation.py -v`
Expected: all PASS.

- [ ] **Step 8: Lint and commit**

Run: `make lint`
Expected: clean.

```bash
git add backend/core/bootstrap.py backend/models/_enums.py backend/schemas/shift.py backend/services/shift_service.py backend/tests/test_shift_service.py
git commit -m "feat(shifts): variance threshold setting, report flag, SHIFT_VARIANCE audit on flagged close"
```

---

### Task 3: Settings PATCH audit (backend)

**Files:**
- Modify: `backend/api/routers/settings.py`
- Test: `backend/tests/test_settings_patch.py`

**Interfaces:**
- Produces: `PATCH /api/settings` (admin) writes `AuditAction.SETTINGS_CHANGED` after commit+flag refresh; `detail="keys=<sorted comma-joined keys>"`. Covers feature-flag toggles (B.8) since `FeatureFlagsTab` uses the same endpoint.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_settings_patch.py` imports:

```python
from backend.models._enums import AuditAction
from backend.repositories import audit_repo
```

Append:

```python
@pytest.mark.asyncio
async def test_patch_settings_audits_settings_changed(
    client: AsyncClient, db: AsyncSession, admin_staff: Staff
):
    res = await client.patch(
        "/api/settings",
        json={"enable_members": "false", "event_banner": "Weekend"},
    )
    assert res.status_code == 200

    logs = await audit_repo.list(db, action=AuditAction.SETTINGS_CHANGED.value)
    assert len(logs) == 1
    assert logs[0].staff_id == admin_staff.id
    assert logs[0].entity_type == "settings"
    assert logs[0].detail == "keys=enable_members,event_banner"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest backend/tests/test_settings_patch.py::test_patch_settings_audits_settings_changed -v`
Expected: FAIL — `logs == []`.

- [ ] **Step 3: Implement the audit**

In `backend/api/routers/settings.py`:

1. Add imports:

```python
from backend.models._enums import AuditAction
from backend.services import audit_service
```

2. Replace the handler with:

```python
@router.patch("")
async def patch_settings(
    updates: dict[str, str],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> dict[str, str]:
    """Update one or more settings rows (admin). Refreshes the flag cache so
    503 gating flips live, and audits the change (B.8)."""
    if not updates:
        raise HTTPException(status_code=400, detail="No settings provided.")
    for key, value in updates.items():
        stmt = select(AppSettings).where(AppSettings.key == key)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = AppSettings(key=key, value=str(value))
            db.add(row)
        else:
            row.value = str(value)
    await db.commit()
    await refresh_flags(db)
    await audit_service.log(
        db,
        action=AuditAction.SETTINGS_CHANGED,
        entity_type="settings",
        entity_id=staff.id if staff else "unknown",
        staff_id=staff.id if staff else None,
        detail=f"keys={','.join(sorted(updates))}",
    )
    result = await db.execute(select(AppSettings))
    return {r.key: r.value for r in result.scalars().all()}
```

- [ ] **Step 4: Run the test file**

Run: `python -m pytest backend/tests/test_settings_patch.py -v`
Expected: all PASS (existing tests unaffected — `_staff` rename to `staff` is behavior-neutral).

- [ ] **Step 5: Lint and commit**

Run: `make lint`
Expected: clean.

```bash
git add backend/api/routers/settings.py backend/tests/test_settings_patch.py
git commit -m "feat(settings): audit SETTINGS_CHANGED on PATCH /api/settings"
```

---

### Task 4: Admin-only license verify endpoint (backend)

**Files:**
- Create: `backend/api/routers/license.py`
- Modify: `backend/api/routers/__init__.py`
- Modify: `backend/models/_enums.py` (`AuditAction.LICENSE_CHECK`)
- Create: `backend/tests/test_license_router.py`
- Modify: `backend/tests/integration/test_ac12_license_verification.py`

**Interfaces:**
- Produces: `POST /api/license/verify` (admin-only) → `{"ok": bool, "error": str | None, "payload": dict | None}`; audits `AuditAction.LICENSE_CHECK` with `entity_id=<hardware_id or "unknown">`, `detail="status=ok"` or `detail="status=error:<reason>"`.
- Consumes: `backend.licensing.verify.check_license()` (sync, never raises), `backend.licensing.fingerprint.get_hardware_id()`.

- [ ] **Step 1: Add the enum member**

In `backend/models/_enums.py`, add next to `SHIFT_VARIANCE`:

```python
    LICENSE_CHECK = "LICENSE_CHECK"
```

- [ ] **Step 2: Create the router**

Create `backend/api/routers/license.py`:

```python
"""License verification API router — admin-only license health check.

Routes::

    POST /api/license/verify → run the offline license check and audit it
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.licensing.verify import LicenseResult, check_license
from backend.models._enums import AuditAction
from backend.models.staff import Staff
from backend.services import audit_service

router = APIRouter(prefix="/license", tags=["license"])


@router.post("/verify")
async def verify_license(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> dict:
    """Verify the local ``license.key`` and audit the result (B.8)."""
    try:
        result = check_license()
    except Exception as exc:  # safety net — check_license() never raises
        raise HTTPException(
            status_code=500, detail=f"License check failed: {exc}"
        ) from exc

    hw_id = result.payload.get("hardware_id") if result.payload else None
    detail = "status=ok" if result.ok else f"status=error:{result.error}"
    await audit_service.log(
        db,
        action=AuditAction.LICENSE_CHECK,
        entity_type="license",
        entity_id=hw_id or "unknown",
        staff_id=staff.id if staff else None,
        detail=detail,
    )
    return {
        "ok": result.ok,
        "error": result.error.value if result.error else None,
        "payload": result.payload,
    }
```

- [ ] **Step 3: Register the router**

In `backend/api/routers/__init__.py`, add the import after the `invoices` import:

```python
from backend.api.routers.license import router as license_router
```

and append `license_router,` to the `routers` list (after `settings_router,`).

- [ ] **Step 4: Write the failing router tests**

Create `backend/tests/test_license_router.py`:

```python
"""Tests for POST /api/license/verify (admin-only, audited)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.licensing.verify import LicenseError, LicenseResult
from backend.main import app
from backend.models._enums import AuditAction, StaffRole
from backend.repositories import audit_repo


def _mock_staff(role: StaffRole) -> object:
    class _S:
        id = "mock-staff-id"
        name = "Mock"
        is_active = True
        token_version = 0

    s = _S()
    s.role = role
    return s


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
async def cashier_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_verify_license_requires_admin(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post("/api/license/verify")
    assert resp.status_code == 403


async def test_verify_license_returns_result_and_audits_ok(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    with patch("backend.api.routers.license.check_license") as mock_check:
        mock_check.return_value = LicenseResult(
            ok=True,
            error=None,
            payload={"hardware_id": "deadbeef", "license_type": "PERPETUAL"},
        )
        resp = await admin_client.post("/api/license/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["error"] is None
    assert body["payload"]["hardware_id"] == "deadbeef"

    logs = await audit_repo.list(db, action=AuditAction.LICENSE_CHECK.value)
    assert len(logs) == 1
    assert logs[0].entity_id == "deadbeef"
    assert logs[0].detail == "status=ok"
    assert logs[0].staff_id == "mock-staff-id"


async def test_verify_license_failure_audits_error(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    with patch("backend.api.routers.license.check_license") as mock_check:
        mock_check.return_value = LicenseResult(
            ok=False, error=LicenseError.MISSING, payload=None
        )
        resp = await admin_client.post("/api/license/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["error"] == "no license.key found"

    logs = await audit_repo.list(db, action=AuditAction.LICENSE_CHECK.value)
    assert len(logs) == 1
    assert logs[0].entity_id == "unknown"
    assert logs[0].detail == "status=error:no license.key found"
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `python -m pytest backend/tests/test_license_router.py -v`
Expected: FAIL — `ImportError: cannot import name 'license_router'` (module not registered yet) or 404.

- [ ] **Step 6: Implement (already done in Steps 2-3) and run**

Run: `python -m pytest backend/tests/test_license_router.py -v`
Expected: all PASS.

- [ ] **Step 7: Replace the skipped AC-12 endpoint test**

In `backend/tests/integration/test_ac12_license_verification.py`, add the import at the top (next to the existing `from backend.licensing import ...`):

```python
from backend.main import app
```

Replace the body of `test_license_endpoint_requires_admin` with:

```python
def test_license_endpoint_requires_admin(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """POST /api/license/verify is admin-only; a cashier gets 403."""
    from backend.api.deps import get_current_staff
    from backend.models._enums import StaffRole

    class _S:
        id = "mock-cashier"
        name = "Cashier"
        is_active = True
        token_version = 0

    s = _S()
    s.role = StaffRole.CASHIER
    app.dependency_overrides[get_current_staff] = lambda: s
    try:
        resp = integration_client.post("/api/license/verify")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_staff, None)
```

(Remove the `pytest.skip(...)` line — no longer skipped.)

- [ ] **Step 8: Run the AC-12 file**

Run: `python -m pytest backend/tests/integration/test_ac12_license_verification.py -v`
Expected: all PASS (the admin path is exercised by `test_license_router.py`; the remaining AC-12 tests are offline signature tests).

- [ ] **Step 9: Lint and commit**

Run: `make lint`
Expected: clean.

```bash
git add backend/api/routers/license.py backend/api/routers/__init__.py backend/models/_enums.py backend/tests/test_license_router.py backend/tests/integration/test_ac12_license_verification.py
git commit -m "feat(license): admin-only POST /api/license/verify with LICENSE_CHECK audit"
```

---

### Task 5: B.2 — stored PINs are Argon2id hashes (verification test)

**Files:**
- Create: `backend/tests/test_pin_hashing.py`

**Interfaces:**
- Consumes: `backend.core.security.hash_pin`, `backend.repositories.staff_repo.create`.
- Produces: verification evidence for B.2.

- [ ] **Step 1: Write the test**

Create `backend/tests/test_pin_hashing.py`:

```python
"""B.2 — stored PINs are Argon2id hashes, never plaintext."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.core.security import hash_pin
from backend.models._enums import StaffRole
from backend.repositories import staff_repo


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


def test_hash_pin_produces_argon2id() -> None:
    hashed = hash_pin("1234")
    assert hashed.startswith("$argon2id$")
    assert "1234" not in hashed


async def test_created_staff_stores_hash_not_plaintext(db: AsyncSession) -> None:
    created = await staff_repo.create(
        db,
        name="Test Cashier",
        pin_hash=hash_pin("9999"),
        role=StaffRole.CASHIER.value,
        is_active=True,
    )
    assert created.pin_hash.startswith("$argon2id$")
    assert "9999" not in created.pin_hash
```

- [ ] **Step 2: Run the tests**

Run: `python -m pytest backend/tests/test_pin_hashing.py -v`
Expected: all PASS (verification evidence for B.2 — no implementation change expected).

- [ ] **Step 3: Lint and commit**

Run: `make lint`
Expected: clean.

```bash
git add backend/tests/test_pin_hashing.py
git commit -m "test: verify stored staff PINs are Argon2id hashes (B.2)"
```

---

### Task 6: B.4 — cashier permissions matrix (verification test)

**Files:**
- Create: `backend/tests/test_permissions_matrix.py`

**Interfaces:**
- Produces: verification evidence for B.4 — a cashier gets 403 on: `PATCH /api/settings` (flag toggle + admin settings), `POST /api/seats/bulk/overlay` (force overlay), `POST /api/backup/run` (backup), `POST /api/staff` (staff management).
- Note: restore-backups (`POST /api/admin/restore`) 403 is deferred to Section L (endpoint does not exist yet).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_permissions_matrix.py`:

```python
"""B.4 — Cashier is denied admin-only operations (403)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.main import app
from backend.models._enums import StaffRole


def _mock_staff(role: StaffRole) -> object:
    class _S:
        id = "mock-staff-id"
        name = "Mock"
        is_active = True
        token_version = 0

    s = _S()
    s.role = role
    return s


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
async def cashier_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_cashier_cannot_patch_settings(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.patch(
        "/api/settings", json={"enable_members": "false"}
    )
    assert resp.status_code == 403


async def test_cashier_cannot_toggle_feature_flag(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.patch(
        "/api/settings", json={"enable_reservations": "false"}
    )
    assert resp.status_code == 403


async def test_cashier_cannot_force_bulk_overlay(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post(
        "/api/seats/bulk/overlay", json={"show": True}
    )
    assert resp.status_code == 403


async def test_cashier_cannot_run_backup(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post("/api/backup/run")
    assert resp.status_code == 403


async def test_cashier_cannot_create_staff(cashier_client: AsyncClient) -> None:
    resp = await cashier_client.post(
        "/api/staff",
        json={"name": "Hacker", "role": "ADMIN", "pin": "1234", "is_active": True},
    )
    assert resp.status_code == 403


async def test_cashier_can_bill_pos(cashier_client: AsyncClient) -> None:
    """B.4 positive: cashier may bill + run POS (not blocked by admin gate)."""
    resp = await cashier_client.post("/api/pos/items")
    assert resp.status_code != 403
```

- [ ] **Step 2: Run the tests**

Run: `python -m pytest backend/tests/test_permissions_matrix.py -v`
Expected: all PASS (pure verification — the 403 gates already exist; `test_cashier_can_bill_pos` asserts the cashier path is not admin-gated).

- [ ] **Step 3: Lint and commit**

Run: `make lint`
Expected: clean.

```bash
git add backend/tests/test_permissions_matrix.py
git commit -m "test: B.4 cashier permissions matrix (admin ops -> 403)"
```

---

### Task 7: B.8 — audit completeness run (verification test)

**Files:**
- Create: `backend/tests/test_audit_completeness.py`

**Interfaces:**
- Consumes: `auth_service.login`, `session_service.start_session`, `billing_service.checkout_session`, `shift_service.open_shift`/`close_shift`, `remote_command_service.restart_seat`, `backup_service.run_backup`, `audit_repo.list`, plus the settings + license HTTP routes from Tasks 3-4.
- Produces: verification evidence for B.8 — login, session start/checkout, shift close, remote restart, settings change, feature flag toggle, backup, and license check all appear in the audit log with staff id, timestamp, action, entity, detail.

- [ ] **Step 1: Write the test**

Create `backend/tests/test_audit_completeness.py`:

```python
"""B.8 — every sensitive operation appears in the audit log.

Drives the real write paths (services + HTTP routes) and asserts each
operation's audit entry exists with staff id, timestamp, action, entity,
and detail.
"""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.security import hash_pin
from backend.licensing.verify import LicenseResult
from backend.main import app
from backend.models import PricingModel
from backend.models._enums import (
    AuditAction,
    PaymentMethod,
    SeatStatus,
    StaffRole,
)
from backend.repositories import audit_repo, seat_repo, staff_repo
from backend.services import (
    auth_service,
    backup_service,
    billing_service,
    remote_command_service,
    session_service,
    shift_service,
)

STAFF_ID = "cashier-1"


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """File-based SQLite (test_audit.py pattern)."""
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


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncClient:
    from backend.models.staff import Staff

    class _Admin:
        id = STAFF_ID
        name = "Cashier"
        is_active = True
        token_version = 0

    admin = _Admin()
    admin.role = StaffRole.ADMIN
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def _seed_staff_and_zone_seat(db: AsyncSession) -> tuple[str, str, str]:
    """Create cashier staff + a zone + an available seat; return their ids."""
    from backend.models import Zone

    staff = await staff_repo.create(
        db,
        name="Cashier One",
        pin_hash=hash_pin("1234"),
        role=StaffRole.CASHIER.value,
        is_active=True,
    )
    zone = Zone(
        name="Main",
        rate_per_minute_paise=100,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    seat.status = SeatStatus.AVAILABLE
    await db.flush()
    return staff.id, zone.id, seat.id


async def test_all_sensitive_ops_are_audited(db: AsyncSession, admin_client: AsyncClient) -> None:
    """One flow: login, session, checkout, restart, settings, flag, backup,
    license, shift close — every one leaves an audit trail."""
    staff_id, _zone_id, seat_id = await _seed_staff_and_zone_seat(db)

    # 1. STAFF_LOGIN — real login with matching PIN
    await auth_service.login(db, "cashier-1", "1234", "127.0.0.1")

    # 2. SESSION_START + 3. CHECKOUT
    started = await session_service.start_session(db, seat_id, staff=None)
    await billing_service.checkout_session(
        db, started.id, PaymentMethod.CASH, staff=None
    )

    # 4. SEAT_RESTARTED — agent send mocked; the audit is the point
    with patch.object(
        remote_command_service, "_send_to_agent_or_503", new=AsyncMock()
    ):
        await remote_command_service.restart_seat(db, seat_id, staff=None)

    # 5. SETTINGS_CHANGED via PATCH (also covers 6. feature-flag toggle)
    resp = await admin_client.patch(
        "/api/settings", json={"enable_reservations": "false", "event_banner": "Tourney"}
    )
    assert resp.status_code == 200
    resp = await admin_client.patch(
        "/api/settings", json={"block_shift_close_unprinted": "true"}
    )
    assert resp.status_code == 200

    # 7. LICENSE_CHECK via the new endpoint
    with patch("backend.api.routers.license.check_license") as mock_check:
        mock_check.return_value = LicenseResult(ok=True, payload={"hardware_id": "abc"})
        resp = await admin_client.post("/api/license/verify")
    assert resp.status_code == 200

    # 8. BACKUP_CREATED — tmp dir overrides
    with tempfile.TemporaryDirectory() as tmp:
        backup_source = Path(tmp) / "src.db"
        backup_source.write_bytes(b"x")
        await backup_service.run_backup(
            db, source_db=backup_source, backup_dir=Path(tmp), staff_id=staff_id
        )

    # 9. SHIFT_CLOSE
    await shift_service.open_shift(db, staff_id=staff_id, opening_cash_paise=5000)
    await shift_service.close_shift(db, staff_id=staff_id, closing_cash_paise=6500)

    expected = {
        AuditAction.STAFF_LOGIN,
        AuditAction.SESSION_START,
        AuditAction.CHECKOUT,
        AuditAction.SEAT_RESTARTED,
        AuditAction.SETTINGS_CHANGED,
        AuditAction.LICENSE_CHECK,
        AuditAction.BACKUP_CREATED,
        AuditAction.SHIFT_CLOSE,
    }
    logs = await audit_repo.list(db, limit=500)
    seen = {AuditAction(entry.action) for entry in logs}
    for action in expected:
        assert action in seen, f"missing audit entry: {action}"

    # Every entry has staff id, timestamp, action, entity, detail
    for entry in logs:
        assert entry.action
        assert entry.entity_type
        assert entry.timestamp is not None
    # Settings changes were attributed to the acting admin
    settings_logs = [e for e in logs if e.action == AuditAction.SETTINGS_CHANGED.value]
    assert len(settings_logs) == 2
    assert all(e.staff_id == STAFF_ID for e in settings_logs)
    assert all(e.detail and "keys=" in e.detail for e in settings_logs)
```

- [ ] **Step 2: Run the test and fix signature mismatches**

Run: `python -m pytest backend/tests/test_audit_completeness.py -v`
Expected: all PASS. If a service signature differs (e.g. `start_session` requires `staff=` positionally), adjust the call minimally — the audit entry is the assertion.

- [ ] **Step 3: Lint and commit**

Run: `make lint`
Expected: clean.

```bash
git add backend/tests/test_audit_completeness.py
git commit -m "test: B.8 audit completeness run (all sensitive ops logged)"
```

---

### Task 8: B.9 — audit API is read-only (verification test)

**Files:**
- Create: `backend/tests/test_audit_immutability_api.py`

**Interfaces:**
- Produces: verification evidence for B.9 — no `PUT`/`DELETE` routes exist under `/api/audit*`.

- [ ] **Step 1: Write the test**

Create `backend/tests/test_audit_immutability_api.py`:

```python
"""B.9 — the audit API exposes read-only routes only."""

from __future__ import annotations

from backend.main import app


def test_audit_routes_are_read_only() -> None:
    audit_methods = {
        (method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/audit")
        for method in getattr(route, "methods", set()) or set()
    }
    assert audit_methods, "expected at least one audit route"
    mutating = {
        (m, p) for (m, p) in audit_methods if m in {"PUT", "DELETE", "PATCH", "POST"}
    }
    assert mutating == set(), f"mutating audit routes found: {mutating}"
    assert any(m == "GET" for m, _ in audit_methods)
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest backend/tests/test_audit_immutability_api.py -v`
Expected: PASS (only `GET /api/audit` and `GET /api/audit/{id}` exist today).

- [ ] **Step 3: Lint and commit**

Run: `make lint`
Expected: clean.

```bash
git add backend/tests/test_audit_immutability_api.py
git commit -m "test: B.9 audit API is read-only (no PUT/DELETE /api/audit*)"
```

---

### Task 9: Frontend shift API client + types

**Files:**
- Create: `frontend/src/types/shift.ts`
- Create: `frontend/src/api/shifts.ts`
- Create: `frontend/src/api/__tests__/shiftsApi.test.ts`

**Interfaces:**
- Produces: `fetchCurrentShift(token) -> Promise<ShiftCurrentResponse | null>`, `openShift(token, floatPaise)`, `closeShift(token, countedPaise)`, hooks `useCurrentShift()` (30s refetch), `useOpenShift()`, `useCloseShift()` — consumed by Task 10.
- Consumes: `useAuthStore` (`accessToken`), TanStack Query.

- [ ] **Step 1: Write the failing types + client tests**

Create `frontend/src/api/__tests__/shiftsApi.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchCurrentShift,
  openShift,
  closeShift,
} from '@/api/shifts';

const TOKEN = 'tok';

beforeEach(() => {
  vi.restoreAllMocks();
});

const OPEN_SHIFT = {
  id: 's1',
  opened_by_staff_id: 'cashier-1',
  closed_by_staff_id: null,
  opened_at: '2026-08-13T10:00:00Z',
  closed_at: null,
  float_paise: 5000,
  counted_paise: null,
  status: 'OPEN',
};

describe('shift API', () => {
  it('fetchCurrentShift GETs /shifts/current with auth', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ shift: OPEN_SHIFT, session_count: 0, total_revenue_paise: 0, average_duration_seconds: 0, expected_cash_paise: 5000 }), { status: 200 }),
    );
    const res = await fetchCurrentShift(TOKEN);
    expect(res?.shift.id).toBe('s1');
    expect(spy.mock.calls[0][0]).toContain('/shifts/current');
    expect(spy.mock.calls[0][1]?.headers).toMatchObject({ Authorization: 'Bearer tok' });
  });

  it('fetchCurrentShift returns null when no shift is open', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(null), { status: 200 }),
    );
    expect(await fetchCurrentShift(TOKEN)).toBeNull();
  });

  it('openShift POSTs float in paise', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(OPEN_SHIFT), { status: 201 }),
    );
    await openShift(TOKEN, 5000);
    expect(spy.mock.calls[0][0]).toContain('/shifts/open');
    expect(spy.mock.calls[0][1]?.method).toBe('POST');
    expect(JSON.parse(spy.mock.calls[0][1]?.body as string)).toEqual({ float_paise: 5000 });
  });

  it('closeShift POSTs counted cash in paise', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ...OPEN_SHIFT, status: 'CLOSED', counted_paise: 6500 }), { status: 200 }),
    );
    await closeShift(TOKEN, 6500);
    expect(spy.mock.calls[0][0]).toContain('/shifts/close');
    expect(spy.mock.calls[0][1]?.method).toBe('POST');
    expect(JSON.parse(spy.mock.calls[0][1]?.body as string)).toEqual({ counted_paise: 6500 });
  });

  it('closeShift surfaces the backend 409 detail (unprinted gate)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE:count=1' }), { status: 409 }),
    );
    await expect(closeShift(TOKEN, 6500)).rejects.toThrow('UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/api/__tests__/shiftsApi.test.ts`
Expected: FAIL — cannot find module `@/api/shifts`.

- [ ] **Step 3: Create the types**

Create `frontend/src/types/shift.ts`:

```ts
export interface ShiftResponse {
  id: string;
  opened_by_staff_id: string;
  closed_by_staff_id: string | null;
  opened_at: string;
  closed_at: string | null;
  float_paise: number;
  counted_paise: number | null;
  status: 'OPEN' | 'CLOSED';
}

export interface ShiftCurrentResponse {
  shift: ShiftResponse;
  session_count: number;
  total_revenue_paise: number;
  average_duration_seconds: number;
  expected_cash_paise: number;
}
```

- [ ] **Step 4: Create the API client**

Create `frontend/src/api/shifts.ts` (mirrors `analytics.ts`):

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type { ShiftCurrentResponse, ShiftResponse } from '@/types/shift';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export async function fetchCurrentShift(
  token: string | null,
): Promise<ShiftCurrentResponse | null> {
  const res = await fetch(`${API_BASE}/shifts/current`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load current shift: ${res.status}`);
  return (await res.json()) as ShiftCurrentResponse | null;
}

export async function openShift(token: string | null, floatPaise: number): Promise<ShiftResponse> {
  const res = await fetch(`${API_BASE}/shifts/open`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ float_paise: floatPaise }),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to open shift: ${res.status}`);
  }
  return (await res.json()) as ShiftResponse;
}

export async function closeShift(token: string | null, countedPaise: number): Promise<ShiftResponse> {
  const res = await fetch(`${API_BASE}/shifts/close`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ counted_paise: countedPaise }),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to close shift: ${res.status}`);
  }
  return (await res.json()) as ShiftResponse;
}

export function useCurrentShift() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['shifts', 'current'],
    queryFn: () => fetchCurrentShift(token),
    enabled: !!token,
    refetchInterval: 30_000,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });
}

export function useOpenShift() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (floatPaise: number) => openShift(token, floatPaise),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shifts', 'current'] });
    },
  });
}

export function useCloseShift() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (countedPaise: number) => closeShift(token, countedPaise),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shifts', 'current'] });
    },
  });
}
```

- [ ] **Step 5: Run the tests**

Run: `npx vitest run src/api/__tests__/shiftsApi.test.ts`
Expected: all PASS.

- [ ] **Step 6: Lint and commit**

Run: `npm run lint` (in `frontend/`)
Expected: clean.

```bash
git add frontend/src/types/shift.ts frontend/src/api/shifts.ts frontend/src/api/__tests__/shiftsApi.test.ts
git commit -m "feat(frontend): shift API client + hooks (current/open/close)"
```

---

### Task 10: Frontend ShiftModal component

**Files:**
- Create: `frontend/src/components/ShiftModal.tsx`
- Create: `frontend/src/components/__tests__/ShiftModal.test.tsx`

**Interfaces:**
- Consumes: `useCurrentShift`/`useOpenShift`/`useCloseShift` (Task 9), `useSettings` (`@/api/settings`), `formatPaise` (`@/hooks/useFormatPaise`), `Modal` (`@/components/ui/Modal`), `Button` (`@/components/ui/Button`, variants `primary`/`secondary`/`danger`), `Input` (`@/components/ui/Input`), `toast` (`@/store/toastStore`).
- Produces: `<ShiftModal open onClose />` — open form (no shift), live totals (shift open), close form with variance preview + threshold warning banner, 409 unprinted-block error toast.

- [ ] **Step 1: Write the failing component tests**

Create `frontend/src/components/__tests__/ShiftModal.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShiftModal } from './ShiftModal';
import type { ShiftCurrentResponse } from '@/types/shift';

const OPEN_CURRENT: ShiftCurrentResponse = {
  shift: {
    id: 's1',
    opened_by_staff_id: 'cashier-1',
    closed_by_staff_id: null,
    opened_at: '2026-08-13T10:00:00Z',
    closed_at: null,
    float_paise: 5000,
    counted_paise: null,
    status: 'OPEN',
  },
  session_count: 3,
  total_revenue_paise: 2500,
  average_duration_seconds: 1800,
  expected_cash_paise: 7500,
};

let openShiftMutate: (...args: unknown[]) => void;
let closeShiftMutate: (...args: unknown[]) => void;
let currentData: ShiftCurrentResponse | null;
let thresholdPaise = '5000';

vi.mock('@/api/shifts', () => ({
  useCurrentShift: () => ({ data: currentData, isPending: false }),
  useOpenShift: () => ({ mutate: (...a: unknown[]) => openShiftMutate(...a), isPending: false }),
  useCloseShift: () => ({ mutate: (...a: unknown[]) => closeShiftMutate(...a), isPending: false }),
}));

vi.mock('@/api/settings', () => ({
  useSettings: () => ({ data: { shift_cash_variance_threshold: thresholdPaise } }),
}));

vi.mock('@/store/toastStore', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

beforeEach(() => {
  currentData = null;
  thresholdPaise = '5000';
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ShiftModal', () => {
  it('shows the open form when no shift is open', () => {
    currentData = null;
    render(<ShiftModal open onClose={() => {}} />);
    expect(screen.getByLabelText(/cash float/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /open shift/i })).toBeInTheDocument();
  });

  it('opens a shift with the float converted to paise', async () => {
    currentData = null;
    let received: number | undefined;
    openShiftMutate = (paise: number) => {
      received = paise;
    };
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/cash float/i), { target: { value: '50' } });
    fireEvent.click(screen.getByRole('button', { name: /open shift/i }));
    expect(received).toBe(5000);
  });

  it('shows live totals when a shift is open', () => {
    currentData = OPEN_CURRENT;
    render(<ShiftModal open onClose={() => {}} />);
    expect(screen.getByText('Rs. 25.00')).toBeInTheDocument(); // revenue
    expect(screen.getByText('3')).toBeInTheDocument(); // sessions
    expect(screen.getByText('30 min')).toBeInTheDocument(); // avg duration
  });

  it('closes the shift with counted cash in paise', async () => {
    currentData = OPEN_CURRENT;
    let received: number | undefined;
    closeShiftMutate = (paise: number) => {
      received = paise;
    };
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    fireEvent.change(screen.getByLabelText(/counted cash/i), { target: { value: '76' } });
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    expect(received).toBe(7600);
  });

  it('shows a warning banner when variance exceeds the threshold', () => {
    currentData = OPEN_CURRENT;
    thresholdPaise = '100';
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    fireEvent.change(screen.getByLabelText(/counted cash/i), { target: { value: '80' } });
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('toasts an error when close is blocked by unprinted invoices', async () => {
    const { toast } = await import('@/store/toastStore');
    currentData = OPEN_CURRENT;
    closeShiftMutate = (_paise: number, opts: { onError: (e: Error) => void }) => {
      opts.onError(new Error('UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE:count=1'));
    };
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        expect.stringContaining('UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE'),
      );
    });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/components/__tests__/ShiftModal.test.tsx`
Expected: FAIL — cannot find module `./ShiftModal`.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/ShiftModal.tsx`:

```tsx
import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useCloseShift, useCurrentShift, useOpenShift } from '@/api/shifts';
import { useSettings } from '@/api/settings';
import { toast } from '@/store/toastStore';
import { formatPaise } from '@/hooks/useFormatPaise';

interface ShiftModalProps {
  open: boolean;
  onClose: () => void;
}

function parseRupeesToPaise(value: string): number {
  const amount = Number.parseFloat(value);
  if (Number.isNaN(amount) || amount < 0) return 0;
  return Math.round(amount * 100);
}

export function ShiftModal({ open, onClose }: ShiftModalProps) {
  const { data: current, isPending } = useCurrentShift();
  const openShift = useOpenShift();
  const closeShift = useCloseShift();
  const { data: settings } = useSettings();

  const [view, setView] = useState<'open' | 'live' | 'close'>('open');
  const [floatRupees, setFloatRupees] = useState('');
  const [countedRupees, setCountedRupees] = useState('');

  const rawThreshold = settings?.shift_cash_variance_threshold;
  const parsedThreshold = rawThreshold ? Number.parseInt(rawThreshold, 10) : 5000;
  const thresholdPaise = Number.isNaN(parsedThreshold) ? 5000 : parsedThreshold;

  const countedPaise = parseRupeesToPaise(countedRupees);
  const expectedPaise = current?.expected_cash_paise ?? 0;
  const variancePaise = countedPaise - expectedPaise;
  const varianceFlagged = Math.abs(variancePaise) > thresholdPaise;

  const handleOpen = () => {
    openShift.mutate(parseRupeesToPaise(floatRupees), {
      onSuccess: () => {
        toast.success('Shift opened');
        setView('live');
        setFloatRupees('');
      },
      onError: (err) => toast.error(err.message ?? 'Failed to open shift'),
    });
  };

  const handleClose = () => {
    closeShift.mutate(countedPaise, {
      onSuccess: () => {
        toast.success('Shift closed');
        setView('open');
        setCountedRupees('');
        onClose();
      },
      onError: (err) => toast.error(err.message ?? 'Failed to close shift'),
    });
  };

  const goToClose = () => {
    setCountedRupees((expectedPaise / 100).toFixed(2));
    setView('close');
  };

  if (isPending) {
    return (
      <Modal open={open} onClose={onClose} title="Shift">
        <p className="text-sm text-muted-foreground">Loading shift…</p>
      </Modal>
    );
  }

  if (current === null) {
    return (
      <Modal open={open} onClose={onClose} title="Shift">
        <div className="space-y-4">
          <Input
            id="float-rupees"
            label="Cash float (₹)"
            type="number"
            min="0"
            step="0.01"
            value={floatRupees}
            onChange={(e) => setFloatRupees(e.target.value)}
            placeholder="0.00"
          />
          <Button
            onClick={handleOpen}
            loading={openShift.isPending}
            disabled={openShift.isPending}
            className="w-full"
          >
            Open Shift
          </Button>
        </div>
      </Modal>
    );
  }

  if (view === 'close') {
    return (
      <Modal open={open} onClose={onClose} title="Close Shift">
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Expected cash: {formatPaise(expectedPaise)}
          </p>
          <Input
            id="counted-rupees"
            label="Counted cash (₹)"
            type="number"
            min="0"
            step="0.01"
            value={countedRupees}
            onChange={(e) => setCountedRupees(e.target.value)}
          />
          {countedRupees !== '' && (
            <p className={`text-sm ${varianceFlagged ? 'text-destructive' : 'text-muted-foreground'}`}>
              Variance: {variancePaise >= 0 ? '+' : ''}
              {formatPaise(Math.abs(variancePaise))}
            </p>
          )}
          {varianceFlagged && (
            <p
              role="alert"
              className="rounded-md bg-destructive/15 p-3 text-sm text-destructive"
            >
              Variance exceeds the threshold of {formatPaise(thresholdPaise)}.
            </p>
          )}
          <Button
            variant="danger"
            onClick={handleClose}
            loading={closeShift.isPending}
            disabled={closeShift.isPending}
            className="w-full"
          >
            Close Shift
          </Button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={onClose} title="Shift">
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Opened with {formatPaise(current.shift.float_paise)} on{' '}
          {new Date(current.shift.opened_at).toLocaleString()}
        </p>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-secondary/50 p-3">
            <p className="text-xs text-muted-foreground">Revenue</p>
            <p className="text-lg font-bold">{formatPaise(current.total_revenue_paise)}</p>
          </div>
          <div className="rounded-lg bg-secondary/50 p-3">
            <p className="text-xs text-muted-foreground">Sessions</p>
            <p className="text-lg font-bold">{current.session_count}</p>
          </div>
          <div className="rounded-lg bg-secondary/50 p-3">
            <p className="text-xs text-muted-foreground">Avg duration</p>
            <p className="text-lg font-bold">
              {Math.round(current.average_duration_seconds / 60)} min
            </p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Expected cash: {formatPaise(current.expected_cash_paise)}
        </p>
        <Button onClick={goToClose} className="w-full">
          Close Shift
        </Button>
      </div>
    </Modal>
  );
}
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/components/__tests__/ShiftModal.test.tsx`
Expected: all PASS. (If `@testing-library/jest-dom` matchers like `toBeInTheDocument` are not registered globally in this project's `test-setup.ts`, the matchers are already available — check `frontend/src/test-setup.ts` when running.)

- [ ] **Step 5: Lint and commit**

Run: `npm run lint` (in `frontend/`)
Expected: clean.

```bash
git add frontend/src/components/ShiftModal.tsx frontend/src/components/__tests__/ShiftModal.test.tsx
git commit -m "feat(frontend): ShiftModal — open form, live totals, close with variance warning"
```

---

### Task 11: Dashboard wiring — Shift button + modal

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/Dashboard.test.tsx`

**Interfaces:**
- Consumes: `ShiftModal` (Task 10), `useAuthStore` (role — Shift visible to Cashier+).
- Produces: dashboard header "Shift" button that opens the modal.

- [ ] **Step 1: Update the failing test**

In `frontend/src/pages/Dashboard.test.tsx`, add a mock alongside the other component mocks at the top of the file (after the `UnprintedInvoices` mock, around line 19):

```tsx
vi.mock('@/components/ShiftModal', () => ({
  ShiftModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="shift-modal" /> : null,
}));
```

Add this test inside the `describe('DashboardPage', ...)` block:

```tsx
  it('shows the Shift button and opens the shift modal', () => {
    render(<DashboardPage />, { wrapper: makeWrapper() });
    const shiftButton = screen.getByRole('button', { name: /shift/i });
    expect(shiftButton).toBeInTheDocument();
    expect(screen.queryByTestId('shift-modal')).not.toBeInTheDocument();
    fireEvent.click(shiftButton);
    expect(screen.getByTestId('shift-modal')).toBeInTheDocument();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/pages/Dashboard.test.tsx`
Expected: FAIL — no button with name /shift/ (and the un-mocked `ShiftModal` import breaks the render).

- [ ] **Step 3: Wire the button + modal into Dashboard**

In `frontend/src/pages/Dashboard.tsx`:

1. Add the import:

```tsx
import { ShiftModal } from '@/components/ShiftModal';
import { Clock } from 'lucide-react';
```

2. Add state next to `const [isLocking, setIsLocking] = useState(false);`:

```tsx
  const [shiftModalOpen, setShiftModalOpen] = useState(false);
```

3. Add the button in the header, after the admin-only lock button (inside the `flex items-center gap-3` div):

```tsx
            <Button
              variant="secondary"
              onClick={() => setShiftModalOpen(true)}
              aria-label="Open shift modal"
            >
              <Clock className="size-4" aria-hidden="true" />
              <span>Shift</span>
            </Button>
```

4. Render the modal next to `<StaffAlertModal />`:

```tsx
      <ShiftModal open={shiftModalOpen} onClose={() => setShiftModalOpen(false)} />
```

(No `isAdmin` gate — Cashier and Admin both use shifts; the backend already gates the report to admin-only.)

- [ ] **Step 4: Run the test file**

Run: `npx vitest run src/pages/Dashboard.test.tsx`
Expected: all PASS (existing tests unaffected).

- [ ] **Step 5: Lint and commit**

Run: `npm run lint` (in `frontend/`)
Expected: clean.

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.test.tsx
git commit -m "feat(frontend): dashboard Shift button opens ShiftModal (cashier+)"
```

---

### Task 12: B.1–B.9 verification run + docs closeout

**Files:**
- Modify: `docs/TODO.md`

**Interfaces:**
- Consumes: everything from Tasks 1–11.

- [ ] **Step 1: Run the full Section B backend test batch**

Run:

```bash
python -m pytest backend/tests/test_auth.py backend/tests/test_staff_auth.py backend/tests/test_auth_service.py backend/tests/test_pin_hashing.py backend/tests/test_shift_service.py backend/tests/test_shifts_router.py backend/tests/test_settings_patch.py backend/tests/test_license_router.py backend/tests/test_permissions_matrix.py backend/tests/test_audit.py backend/tests/test_audit_completeness.py backend/tests/test_audit_immutability_api.py backend/tests/test_invoice_router_print_gate.py backend/tests/integration/test_ac09_audit_immutability.py backend/tests/integration/test_ac10_shift_reconciliation.py backend/tests/integration/test_ac12_license_verification.py
```

Expected: all PASS. Fix any failure via reproduce → minimal fix → regression test → verify.

- [ ] **Step 2: Run the full pytest suite to catch regressions**

Run: `python -m pytest backend/tests -x -q`
Expected: all PASS. (Backends untouched areas — auth, sessions, billing — must not regress; the `GET /current` shape change is the only cross-cutting one.)

- [ ] **Step 3: Run the frontend test suite**

Run: `npx vitest run` (in `frontend/`)
Expected: all PASS.

- [ ] **Step 4: Run lint everywhere**

Run: `make lint`
Expected: clean (ruff + mypy strict + ESLint).

- [ ] **Step 5: Map results to the checklist and mark complete**

For each of B.1–B.9 in `docs/TODO.md`:

- B.1 — covered by Task 12 Step 1 (`test_auth`/`test_staff_auth`/`test_auth_service`). Check off.
- B.2 — `test_pin_hashing.py` (Task 5). Check off.
- B.3 — `test_auth_service.py` (token_version). Check off.
- B.4 — `test_permissions_matrix.py` (Task 6); restore deferred to Section L. Check off with that note.
- B.5 — `test_shift_service.py` live-totals tests + manual check: run the app, open a shift with float, confirm the modal shows revenue/sessions/avg duration. Check off.
- B.6 — variance threshold tests (Task 2) + report `variance_flagged`. Check off.
- B.7 — `test_invoice_router_print_gate.py` re-run + modal 409 toast (Task 10 test). Check off.
- B.8 — `test_audit.py`, AC-09, `test_audit_completeness.py`, settings/license audit tests. Check off.
- B.9 — `test_audit_immutability_api.py` + AC-09. Check off.

Replace each `- [ ] **B.N ...` checkbox with `- [x]`, keep the text, and append `(fixed/verified in 2026-08-13 pass)`.

- [ ] **Step 6: Update the project status line**

In `docs/TODO.md`, add a note in the status line: `Section B (auth, staff, shifts & audit) complete — 2026-08-13`.

- [ ] **Step 7: Commit**

```bash
git add docs/TODO.md
git commit -m "docs: mark Section B complete — auth, staff, shifts & audit verified (B.1-B.9)"
```
