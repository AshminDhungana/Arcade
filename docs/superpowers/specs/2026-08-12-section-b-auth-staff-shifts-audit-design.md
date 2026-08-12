# Section B — Auth, Staff, Shifts & Audit: Gap-Closing Design

**Date:** 2026-08-12
**Status:** Approved — awaiting implementation plan
**Source:** `docs/TODO.md` Section B (items B.1–B.9)

## Summary

Section B is a release-testing checklist area. Exploration found the backend for
B.1–B.9 is already implemented and all referenced test files pass. Three real
gaps remain between the checklist intent and the shipped code:

1. **No shift UI in the frontend** — there is no way to open/close a shift or
   see shift-scoped running totals, despite the AC-10 acceptance doc claiming a
   "Shift modal" exists.
2. **Audit gaps for B.8** — `PATCH /api/settings` (which is also how feature
   flags are toggled) writes no audit entry; the license-check endpoint does not
   exist, so "license check" cannot appear in the audit log.
3. **`shift_cash_variance_threshold` does not exist** — B.6 requires variance
   over a threshold to be flagged, but variance is computed and never compared.

The B.4 "restore backups" 403 check is deferred to Section L, where the restore
endpoint (`POST /api/admin/restore`) will be built with its admin gate.

This spec covers: (a) backend shift live totals + variance threshold,
(b) audit logging for settings changes + a new license-check endpoint,
(c) a frontend `ShiftModal`, and (d) the full B.1–B.9 verification run.

## Current State (verified during exploration)

- `backend/services/shift_service.py` — open/close/report fully implemented;
  report computes `session_count`, `invoice_count`, `total_revenue_paise`,
  `pos_total_paise`, `cash_collected_paise`, `expected_cash_paise`,
  `variance_paise`.
- `backend/api/routers/shifts.py` — `POST /open`, `POST /close`,
  `GET /current`, `GET /{shift_id}/report`; open/close/current require cashier+,
  report requires admin.
- `backend/api/routers/settings.py` — `PATCH /api/settings` (admin) writes
  settings + refreshes the flag cache, but logs no audit entry.
- `backend/models/_enums.py:195` — `AuditAction.SETTINGS_CHANGED` exists but is
  unused. No license-related audit action exists.
- `backend/licensing/verify.py:71` — `check_license()` exists, sync, never
  raises; used by the launcher, not by any API route.
- `backend/tests/integration/test_ac12_license_verification.py:204` — the
  `POST /api/license/verify` endpoint test is `pytest.skip`-ed ("endpoint not
  yet implemented").
- `backend/core/bootstrap.py:24` — `DEFAULT_FEATURE_FLAGS` seeds settings rows;
  `ensure_default_feature_flags` inserts only when the settings table is empty.
- Frontend: `KpiRow` shows today-based analytics totals; no shift API client,
  no shift component, no shift references in `Dashboard.tsx`.
- All Section B test files pass today: `test_auth.py`, `test_staff_auth.py`,
  `test_auth_service.py`, `test_shift_service.py`, `test_shifts_router.py`,
  `test_integration/test_ac10_shift_reconciliation.py`,
  `test_invoice_router_print_gate.py`, `test_audit.py`,
  `test_integration/test_ac09_audit_immutability.py`.

## Decision Log (from brainstorming)

| Question | Decision |
|---|---|
| Scope | Full: build missing UI + close audit gaps + variance threshold, then verify B.1–B.9 |
| Shift UI placement | Dashboard header button + modal (matches AC-10 doc) |
| Running totals source | Extend `GET /api/shifts/current` with live shift-scoped totals |
| Variance threshold | DB setting (default ₹50 = 5000 paise, admin-editable), flag field in report + UI warning + `SHIFT_VARIANCE` audit entry on flagged close |
| Audit gaps | Audit `SETTINGS_CHANGED` on `PATCH /api/settings`; build minimal admin-only `POST /api/license/verify` that audits the result |
| Restore 403 check | Deferred to Section L (endpoint built there with admin gate + test) |

## Section 1 — Backend: Shift Live Totals + Variance Threshold

### New schema: `ShiftCurrentResponse`

`backend/schemas/shift.py` gains:

```python
class ShiftCurrentResponse(BaseResponseSchema):
    shift: ShiftResponse
    session_count: int
    total_revenue_paise: int
    average_duration_seconds: float
    expected_cash_paise: int
    variance_flagged: bool
```

- `expected_cash_paise` = `float_paise + sum(invoice.total_paise where payment_method == CASH)`.
- `average_duration_seconds` = mean of `(ended_at - started_at) - total_paused_seconds`
  over completed sessions in the shift; `0.0` when none (same formula as
  `analytics_service.py:388-393`).
- `variance_flagged` = `counted_paise is not None and abs(counted - expected) > threshold`; always `False` while the shift is open (counted is None).

### `shift_service` refactor

- New private helper `_live_totals(db, shift_id)` returning a small dataclass
  (or reused `ShiftReport` fields) computing session count, revenue, avg
  duration, expected cash.
- `get_shift_report()` reuses `_live_totals` instead of computing inline.
- New `get_current_shift_totals(db)` used by the router for `GET /api/shifts/current`
  (returns `None` when no shift is open).
- `ShiftReportResponse` gains `variance_flagged: bool`.

### Variance threshold setting

- New entry in `bootstrap.DEFAULT_FEATURE_FLAGS` (the settings-seeding dict):
  `"shift_cash_variance_threshold": "5000"` (paise, ₹50). Reuses existing
  seeding path — `PATCH /api/settings` already makes it admin-editable.
- Threshold read via the existing settings lookup used by `shift_service`
  (same mechanism as `block_shift_close_unprinted`, which reads the
  `AppSettings` row — see `shift_service.py:111`). Default `5000` paise when
  the row is missing.

### Audit on flagged close

- New enum member `AuditAction.SHIFT_VARIANCE = "SHIFT_VARIANCE"`.
- In `close_shift`, when the computed variance is flagged: audit
  `SHIFT_VARIANCE` with `entity_type="shift"`, `entity_id=shift.id`,
  `staff_id`, `detail=f"variance_paise={v};threshold_paise={t}"`.
- Existing `SHIFT_CLOSE` entry unchanged.

### Router change

`backend/api/routers/shifts.py` `GET /current` returns `ShiftCurrentResponse | None`.

### Affected existing tests

- `test_shifts_router.py:122` asserts `body["expected_cash_paise"] == 5000` on
  the current-shift body — update to the new response shape.
- `test_ac10_shift_reconciliation.py` asserts report fields — additive field,
  safe.
- `test_shift_service.py` — additive; add new cases for live totals and
  threshold flagging.

## Section 2 — Backend: Audit Gaps

### A. `PATCH /api/settings` audits `SETTINGS_CHANGED`

- In `settings.py:patch_settings`, after commit + flag refresh, log:
  `action=AuditAction.SETTINGS_CHANGED`, `entity_type="settings"`,
  `entity_id=staff.id`, `staff_id=staff.id`,
  `detail="keys=<comma-joined changed keys>"`.
- Covers feature-flag toggles (B.8) — `FeatureFlagsTab` writes flags through
  the same `PATCH /api/settings`.
- New tests in `test_settings_patch.py`: audit entry created; detail lists the
  changed keys.

### B. New `POST /api/license/verify` (admin-only)

- New router `backend/api/routers/license.py`, registered in
  `backend/api/routers/__init__.py`.
- Handler: `require_admin`, calls `check_license()` (sync; never raises),
  returns the `LicenseResult` payload as JSON.
- Audits every call: new enum member `AuditAction.LICENSE_CHECK = "LICENSE_CHECK"`,
  `entity_type="license"`, `entity_id=<hardware_id or "unknown">`,
  `detail=f"status={result.status}"`.
- Wrap the call in try/except → 500 as a safety net.

### Affected existing tests

- `test_ac12_license_verification.py:204-210` — un-skip
  `test_license_endpoint_requires_admin`; cashier → 403, admin → 200.
- `test_enums.py` / `test_schemas_audit_settings.py` — verify enum-set
  assertions; add `LICENSE_CHECK`/`SHIFT_VARIANCE` where actions are
  enumerated.

## Section 3 — Frontend: Shift UI

### New API client `frontend/src/api/shifts.ts`

Pattern mirrors `analytics.ts` (fetch + React Query hooks, token from
`useAuthStore`):

- `fetchCurrentShift(token)` → `GET /api/shifts/current`
- `openShift(token, floatPaise)` → `POST /api/shifts/open`
- `closeShift(token, countedPaise)` → `POST /api/shifts/close`
- `fetchShiftReport(token, shiftId)` → `GET /api/shifts/{id}/report`
- Hooks: `useCurrentShift()` (refetchInterval 30s), `useOpenShift()`,
  `useCloseShift()`.

### New types `frontend/src/types/shift.ts`

Matching the backend schemas (`ShiftResponse`, `ShiftCurrentResponse`,
`ShiftReportResponse`), paise as numbers.

### New component `frontend/src/components/ShiftModal.tsx`

Dashboard header button "Shift" (visible to Cashier+; both roles can use
shifts). Follows existing modal patterns (`SeatActionModal.tsx`: Radix Dialog,
motion; `KpiCard` for totals).

**No shift open** → open form: cash float input in ₹ (converted to paise
client-side), "Open Shift" button; success toast, switch to open state.

**Shift open** → live view:
- Running totals from `useCurrentShift()` (revenue ₹, sessions, avg duration),
  refreshed every 30s.
- Expected cash display (float + cash payments so far).
- "Close Shift" → close form: counted-cash input auto-filled with expected
  cash; variance preview; warning banner when `|variance| > threshold`
  (threshold from existing `useSettings` hook, key
  `shift_cash_variance_threshold`).
- Close → `POST /api/shifts/close`; success toast, close modal; on 409
  `UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE`, show the block message.

### Dashboard wiring

`Dashboard.tsx:66-87` header: add "Shift" button next to the admin-only
"Lock all idle seats" button.

### Frontend tests (vitest)

- `api/shifts.test.ts` — fetch/open/close mapping, paise conversion.
- `ShiftModal.test.tsx` — open form when no shift; totals when open; close flow
  calls closeShift with counted paise; warning banner when variance exceeds
  threshold; error toast on 409 block.
- `Dashboard.test.tsx` — Shift button present.

## Section 4 — B.1–B.9 Verification Run

Run each checklist item's verification in order; fix failures per the TODO
fix-workflow (reproduce → minimal fix → regression test → verify → record →
check off).

- **B.1** — `python -m pytest backend/tests/test_auth.py backend/tests/test_staff_auth.py backend/tests/test_auth_service.py`
- **B.2** — manual DB check: `staff.pin_hash` rows start with `$argon2id$`, no
  plaintext (one-off script or pytest).
- **B.3** — `test_auth_service.py` (token_version bump on PIN change).
- **B.4** — new consolidated `test_permissions_matrix.py`: cashier 403 against
  `PATCH /api/settings`, force overlay, `POST /api/backup/run`, staff CRUD.
  Restore deferred to L.
- **B.5** — `test_shift_service.py` + manual UI check (open shift with float,
  modal shows live totals).
- **B.6** — `test_shift_service.py`, `test_shifts_router.py`,
  `test_ac10_shift_reconciliation.py` + new variance-threshold cases.
- **B.7** — `test_invoice_router_print_gate.py` (re-run after changes).
- **B.8** — `test_audit.py`, `test_ac09_audit_immutability.py`, new
  `test_audit_completeness.py` (performs login, session start/checkout, shift
  close, remote restart, settings change, flag toggle, backup, license check;
  asserts each appears with staff_id/timestamp/action/entity/detail), plus new
  settings-change and license-check audit tests.
- **B.9** — checklist: no `PUT/DELETE /api/audit*` routes (only GET exists) +
  `test_ac09` repo-level immutability.
- Lint: `make lint` (ruff + mypy strict + ESLint) after code lands.

## Docs & Closeout

- Mark B.1–B.9 `[x]` in `docs/TODO.md`; add "Fixed during this pass" rows;
  commit; note Section B complete in the project status line.

## Out of Scope

- Restore endpoint (Section L) — B.4 restore-403 deferred.
- Any change to existing auth (login/lockout/token_version) behavior — B.1–B.3
  already pass; only verification runs.
- Mobile owner view (`/mobile`, K.4).
