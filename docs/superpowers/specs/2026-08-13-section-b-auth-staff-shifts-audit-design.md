# Section B — Auth, Staff, Shifts & Audit: Gap-Closing Design

**Date:** 2026-08-13
**Status:** Approved — awaiting implementation plan
**Source:** `docs/TODO.md` Section B (items B.1–B.9)

## Summary

Section B is a release-testing checklist area. Exploration found the backend for
B.1–B.9 is already implemented and the referenced test files pass. Three real
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
  `variance_paise` inline (lines 171-198). No threshold comparison.
- `backend/api/routers/shifts.py` — `POST /open`, `POST /close`,
  `GET /current`, `GET /{shift_id}/report`; open/close/current require cashier+,
  report requires admin. `GET /current` returns bare `ShiftResponse | None`.
- `backend/api/routers/settings.py` — `PATCH /api/settings` (admin) writes
  settings + refreshes the flag cache, but logs no audit entry.
- `backend/models/_enums.py` — `AuditAction.SETTINGS_CHANGED` exists but is
  unused. No license- or variance-related audit action exists.
- `backend/licensing/verify.py:71` — `check_license()` exists, sync, never
  raises; used by the launcher, not by any API route.
- `backend/tests/integration/test_ac12_license_verification.py:204` — the
  `POST /api/license/verify` endpoint test is `pytest.skip`-ed ("endpoint not
  yet implemented").
- `backend/core/bootstrap.py:24` — `DEFAULT_FEATURE_FLAGS` seeds settings rows;
  `ensure_default_feature_flags` inserts only when the settings table is empty
  (existing DBs fall back to code defaults; same pattern as
  `tier_silver_threshold` in `member_service.py`).
- Frontend: `Dashboard.tsx` header (lines 68-87) has no shift entry point; no
  shift API client or component exists. `useSettings` hook exists
  (`frontend/src/api/settings.ts:60`). `SeatActionModal.tsx` is the house modal
  pattern (Radix Dialog + motion).
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
| Variance threshold | DB setting (default 5000 paise = ₹50, admin-editable via existing `PATCH /api/settings`), flag field in report + UI warning + `SHIFT_VARIANCE` audit entry on flagged close |
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
```

- `session_count`, `total_revenue_paise`, `expected_cash_paise` use the same
  math as the close-time report.
- `expected_cash_paise` = `float_paise + sum(invoice.total_paise where
  payment_method == CASH)`.
- `average_duration_seconds` = mean of `(ended_at - started_at) - paused time`
  over completed sessions in the shift; `0.0` when none (same formula as
  `analytics_service`).
- No `variance_flagged` on the live response — counted cash is `None` while
  open so it would always be `False`; a dead field (YAGNI). It lives on the
  report, where it is meaningful.
- `invoice_count` / `pos_total_paise` deliberately omitted from the live
  response — B.5 requires only revenue, sessions, avg duration (YAGNI).

### `shift_service` refactor

- New private helper computing the shared block of computations currently
  inline in `get_shift_report` (lines 171-198): session count, revenue,
  expected cash (and, for the report path, invoice count, POS total, variance).
- `get_shift_report()` reuses the helper instead of computing inline.
- New `get_current_shift_totals(db)` used by the router for `GET /api/shifts/current`
  (returns `None` when no shift is open).
- `ShiftReportResponse` gains `variance_flagged: bool` =
  `counted_paise is not None and abs(variance_paise) > threshold`.

### Variance threshold setting

- New entry in `bootstrap.DEFAULT_FEATURE_FLAGS` (the settings-seeding dict):
  `"shift_cash_variance_threshold": "5000"` (paise, ₹50). Reuses the existing
  seeding path; `PATCH /api/settings` already makes it admin-editable.
- Threshold read as an `AppSettings` row; code default `5000` paise when the
  row is missing (existing DBs that never re-seed). Same mechanism/pattern as
  `tier_silver_threshold` in `member_service.py`.

### Audit on flagged close

- New enum member `AuditAction.SHIFT_VARIANCE = "SHIFT_VARIANCE"`.
- In `close_shift`, after computing `variance = counted_paise - expected_cash`:
  when `abs(variance) > threshold`, audit `SHIFT_VARIANCE` with
  `entity_type="shift"`, `entity_id=shift.id`, `staff_id`,
  `detail=f"variance_paise={v};threshold_paise={t}"`.
- Existing `SHIFT_CLOSE` entry unchanged.

### Router change

`backend/api/routers/shifts.py` `GET /current` returns
`ShiftCurrentResponse | None` instead of `ShiftResponse | None`.

### Affected existing tests

- `test_shifts_router.py` — `GET /current` body shape changes; fix any
  assertions on the current response (report assertions like
  `expected_cash_paise == 5000` at line 122 are unaffected).
- `test_ac10_shift_reconciliation.py` — asserts report fields; additive
  `variance_flagged` field is safe.
- `test_shift_service.py` — additive; add new cases for live totals and
  threshold flagging.

## Section 2 — Backend: Audit Gaps (B.8)

### A. `PATCH /api/settings` audits `SETTINGS_CHANGED`

- In `settings.py:patch_settings`, after commit + flag refresh (lines 55-56),
  log: `action=AuditAction.SETTINGS_CHANGED`, `entity_type="settings"`,
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
  returns the `LicenseResult` payload (`ok`, `error`, `payload`) as JSON.
- Audits every call: new enum member `AuditAction.LICENSE_CHECK = "LICENSE_CHECK"`,
  `entity_type="license"`, `entity_id=<hardware_id or "unknown">`,
  `detail="status=ok"` when `result.ok` else `detail="status=error:<result.error>"`.
- Wrap the sync call in try/except → 500 as a safety net.

### Affected existing tests

- `test_ac12_license_verification.py:204-210` — un-skip
  `test_license_endpoint_requires_admin`; cashier → 403, admin → 200.
- `test_enums.py` / `test_schemas_audit_settings.py` — add
  `LICENSE_CHECK` / `SHIFT_VARIANCE` where audit actions are enumerated.

## Section 3 — Frontend: Shift UI

### New API client `frontend/src/api/shifts.ts` + types `frontend/src/types/shift.ts`

Pattern mirrors `analytics.ts` (fetch + React Query hooks, token from
`useAuthStore`):

- `fetchCurrentShift(token)` → `GET /api/shifts/current`
- `openShift(token, floatPaise)` → `POST /api/shifts/open`
- `closeShift(token, countedPaise)` → `POST /api/shifts/close`
- Hook: `useCurrentShift()` with `refetchInterval: 30_000` (live totals while
  the modal is open).
- Types match backend schemas (`ShiftResponse`, `ShiftCurrentResponse`,
  `ShiftReportResponse`), paise as numbers.

### New component `frontend/src/components/ShiftModal.tsx`

Follows the house modal pattern (`SeatActionModal.tsx`: Radix Dialog, motion;
`useAuthStore` role check). Two states:

**No shift open** → open form: cash float input in ₹ (converted to paise
client-side), "Open Shift" button; success toast, switch to open state.

**Shift open** → live view:
- Running totals from `useCurrentShift()` (revenue, sessions, avg duration),
  refreshed every 30s.
- Expected-cash display (float + cash payments so far).
- "Close Shift" → close form: counted-cash input auto-filled with expected
  cash; variance preview; warning banner when `|variance| > threshold`
  (threshold from existing `useSettings` hook, key
  `shift_cash_variance_threshold`).
- Close → `POST /api/shifts/close`; success toast, close modal, invalidate
  `useCurrentShift`; on 409 `UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE`, show the
  block message (B.7).

### Dashboard wiring

`Dashboard.tsx` header (lines 68-87): "Shift" button next to the admin-only
"Lock all idle seats" button, visible to Cashier+ (both roles can open/close
shifts; the report stays admin-only via the backend gate on
`GET /shifts/{id}/report`). Disabled while a shift action is pending.

### Frontend tests (vitest)

- `api/shifts.test.ts` — fetch/open/close mapping, paise conversion.
- `ShiftModal.test.tsx` — open form when no shift; totals when open; close flow
  calls `closeShift` with counted paise; warning banner when variance exceeds
  threshold; error toast on 409 block.
- `Dashboard.test.tsx` — Shift button present.

## Section 4 — B.1–B.9 Verification Run

Run each checklist item's verification in order after the code lands; fix
failures per the house fix-workflow (reproduce → minimal fix → regression test →
verify → record → check off).

- **B.1** — `python -m pytest backend/tests/test_auth.py backend/tests/test_staff_auth.py backend/tests/test_auth_service.py`
- **B.2** — one-off pytest: `staff.pin_hash` rows start with `$argon2id$`, no
  plaintext in DB.
- **B.3** — `backend/tests/test_auth_service.py` (token_version bump on PIN
  change).
- **B.4** — new consolidated `backend/tests/test_permissions_matrix.py`:
  cashier 403 against `PATCH /api/settings`, force overlay, `POST /api/backup/run`,
  staff CRUD. Restore deferred to Section L.
- **B.5** — `backend/tests/test_shift_service.py` + manual UI check (open
  shift with float, modal shows live totals).
- **B.6** — `backend/tests/test_shift_service.py`, `backend/tests/test_shifts_router.py`,
  `backend/tests/integration/test_ac10_shift_reconciliation.py` + new
  variance-threshold flagging cases.
- **B.7** — `backend/tests/test_invoice_router_print_gate.py` (re-run) + modal
  409 handling covered by Section 3 frontend tests.
- **B.8** — `backend/tests/test_audit.py`, `backend/tests/integration/test_ac09_audit_immutability.py`,
  new `backend/tests/test_audit_completeness.py` (performs login, session
  start/checkout, shift close, remote restart, settings change, flag toggle,
  backup, license check; asserts each appears with staff id/timestamp/action/
  entity/detail), plus new settings-change and license-check audit tests.
- **B.9** — checklist: no `PUT/DELETE /api/audit*` routes (only GET exists) +
  `test_ac09` repo-level immutability.
- `make lint` (ruff + mypy strict + ESLint) after code lands.

## Docs & Closeout

- Mark B.1–B.9 `[x]` in `docs/TODO.md`; add "Fixed during this pass" rows;
  commit; note Section B complete in the project status line.

## Out of Scope

- Restore endpoint (Section L) — B.4 restore-403 deferred.
- Any change to existing auth (login/lockout/token_version) behavior — B.1–B.3
  already pass; only verification runs.
- Mobile owner view (`/mobile`, K.4).
