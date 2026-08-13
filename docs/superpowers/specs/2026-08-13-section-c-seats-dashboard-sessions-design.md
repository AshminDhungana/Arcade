# Section C — Seats, Dashboard & Sessions: Gap-Closing Design

**Date:** 2026-08-13
**Status:** Approved — awaiting implementation plan
**Source:** `docs/TODO.md` Section C (items C.1–C.11)

## Summary

Section C is a release-testing checklist area. Exploration found the backend and
frontend for C.1–C.11 are mostly implemented and all referenced test files pass
today (116 tests verified green: seat lifecycle, sessions, WoL, assigned time,
sync reconcile, recovery). Four real gaps remain between the checklist intent
and the shipped code:

1. **`SeatStatus.ONLINE` is never emitted** — the enum member exists but the
   implementation uses `AVAILABLE` for "agent connected, seat idle", which
   contradicts the docs (SDD §9.4 "Server marks seat as ONLINE", FR-WOL-006,
   AC-07/AC-14 manual checklists) and the C.2/C.6/H.1 checklist wording.
   Related latent bug: `_handle_register` sets `AVAILABLE` **unconditionally**,
   so a mid-session agent reconnect (C.7 LAN drop, C.8 crash) flips an
   IN_USE/PAUSED/EXPIRED seat back to AVAILABLE on the dashboard.
2. **`enable_wake_on_lan` feature flag does not exist** — `boot_all_seats()`
   runs unconditionally at startup (`backend/main.py:120`); C.6 requires a
   flag to gate it.
3. **Maintenance UI is not wired** — the "Maintenance" button in
   `frontend/src/components/SeatActionModal.tsx:155` has no `onClick`; there is
   no way to mark/clear a seat out of order from the dashboard.
4. **No downtime tracking** — SRS FR-SEAT-006 requires per-machine downtime
   duration, but nothing records when maintenance started.

This spec covers: (a) real ONLINE status with correct reconnect semantics,
(b) the `enable_wake_on_lan` flag, (c) downtime tracking via a
`maintenance_since` column, (d) maintenance UI wiring, (e) new regression tests
for C.4/C.7/C.8, and (f) the full C.1–C.11 verification run.

## Current State (verified during exploration)

- `backend/models/_enums.py` — `SeatStatus.ONLINE = "ONLINE"` exists but has no
  writers; the active states are OFFLINE, BOOTING, AVAILABLE, IN_USE, PAUSED,
  EXPIRED, RESERVED, MAINTENANCE, UNREACHABLE.
- `backend/core/ws_manager.py:352` — `_handle_register` sets
  `seat.status = AVAILABLE` unconditionally on every REGISTER (agent sends
  REGISTER on **every** connect/reconnect, `agent/src/main/ws/client.ts:439`).
  Also fires `wol_success_callback` (wol_service.py:299, sets AVAILABLE when
  BOOTING).
- `backend/services/wol_service.py` — magic packet structure (102 bytes,
  broadcast :9), `send_wol_to_seat` → BOOTING + 60s watchdog → UNREACHABLE,
  `boot_all_seats` (line 223) sends to every seat with a MAC, unconditionally
  called from `backend/main.py:120`.
- `backend/services/session_service.py:181` — `start_session` accepts
  {AVAILABLE, RESERVED}; resolves and locks the rate (`locked_rate_paise`,
  `locked_pricing_model`) at start (C.3 OK).
- `backend/services/billing_service.py` — `_release_held_seat` (line 242) and
  the release path (line 572) set seat → AVAILABLE; checkout gates on session
  status, not seat status.
- `backend/services/reservation_service.py:305` — reserve requires AVAILABLE.
  `backend/services/remote_command_service.py:437` — "lock all idle seats"
  targets AVAILABLE.
- `backend/services/seat_service.py:157-235` — `set_maintenance` /
  `clear_maintenance` implemented (admin-only routes in
  `backend/api/routers/seats.py:181,195`, audit entries
  `SEAT_MAINTENANCE_ON/OFF`). The seat already has a `notes` column for the
  note. No maintenance timestamp anywhere.
- `backend/core/bootstrap.py:24` — `DEFAULT_FEATURE_FLAGS` (16 entries) has no
  WoL flag. `get_flag(name)` returns False for unknown flags
  (`core/feature_flags.py:57`), so gating on a new flag is safe.
- Frontend: `SeatStatusBadge.tsx` / `SeatCard.tsx` color maps cover all statuses
  except ONLINE; `SeatActionModal.tsx` Start Session gate is
  `status === 'AVAILABLE'`; Maintenance button is dead. `SeatGrid.tsx` opens
  `SeatActionModal` for idle seats and `SessionDrawer` for in-use.
- All Section C test files pass today: `test_seat_status_integration.py`,
  `test_wol_service.py`, `test_sessions_router.py`, `test_session_service.py`,
  `test_assigned_time_e2e.py`, `test_sweep_expired_sessions.py`,
  `integration/test_ac01_ws_latency.py`, `test_ac04_wol_packet.py`,
  `test_ac02_api_performance.py`, `test_ac07_sync_reconcile.py`,
  `test_ac22_session_persistence.py`.

## Decision Log (from brainstorming)

| Question | Decision |
|---|---|
| ONLINE status | Implement for real: agent-connected idle → ONLINE; both ONLINE and AVAILABLE remain startable |
| Mid-session reconnect | `_handle_register` must NOT touch IN_USE/PAUSED/EXPIRED/RESERVED/MAINTENANCE (fixes latent C.7/C.8 display bug) |
| `enable_wake_on_lan` default | **ON** (preserves current behavior; flag exists so operators can disable; skip MAINTENANCE seats on boot) |
| Downtime tracking | `maintenance_since` timestamp column on `seats` (alembic migration) + live duration in `SeatResponse` + display in seat modal |
| Maintenance UI | Wire the existing button in `SeatActionModal` (set with note / clear), Admin-only, hidden for Cashier |
| C.1 timing | Keep AC-01's 1 s test as the automated gate (matches NFR-PERF-001); the checklist's <100 ms is verified manually with two dashboard tabs |
| C.5 "50 concurrent" | `test_ac02_api_performance.py` is the gate; the Locust load suite (`backend/tests/load/`) covers 50-agent scale and stays optional |
| Release after checkout | Stays AVAILABLE ("released, ready"); ONLINE only enters via agent REGISTER. C.2's lifecycle renders verbatim |

## Section 1 — Backend: ONLINE Seats & Safe Reconnect

### State transitions

| Trigger | Old behavior | New behavior |
|---|---|---|
| REGISTER, seat ∈ {OFFLINE, BOOTING, UNREACHABLE, AVAILABLE} | → AVAILABLE | → **ONLINE** |
| REGISTER, seat ∈ {IN_USE, PAUSED, EXPIRED, RESERVED, MAINTENANCE} | → **AVAILABLE** (clobbers live state — bug) | **no change** |
| WoL success (`wol_success_callback`, seat BOOTING) | → AVAILABLE | → **ONLINE** |
| Watchdog timeout (60 s, still BOOTING) | → UNREACHABLE | unchanged |
| `start_session` gate | {AVAILABLE, RESERVED} | {AVAILABLE, **ONLINE**, RESERVED} → IN_USE |
| Checkout / force-release / clear-maintenance / WOL override | → AVAILABLE | unchanged |
| Agent disconnect / heartbeat timeout | → OFFLINE | unchanged |

### Implementation notes

- `backend/core/ws_manager.py:_handle_register` — compute the transition from
  the current DB status; only OFFLINE/BOOTING/UNREACHABLE/AVAILABLE → ONLINE.
  Broadcast unchanged. Keep the `overlay_forced` re-push and the
  `wol_success_callback` task firing.
- `backend/services/wol_service.py:wol_success_callback` — BOOTING → ONLINE
  (was AVAILABLE). The register handler already sets ONLINE in the same flow,
  so this only keeps the callback consistent for direct calls.
- Gates updated to accept ONLINE:
  - `backend/services/session_service.py:181` (start_session)
  - `backend/services/reservation_service.py:305` (reserve only on
    AVAILABLE/ONLINE)
  - `backend/services/remote_command_service.py:437` (bulk idle-seat targets:
    AVAILABLE + ONLINE)
- No change: Unreachable → register → ONLINE works via the transition table
  (watchdog-exceeded seats recover automatically when the agent finally
  registers).

### Frontend (ONLINE rendering)

- `SeatStatusBadge.tsx` + `SeatCard.tsx`: add ONLINE (teal
  `bg-teal-500`/`border-l-teal-500`, label "Online") to both maps.
- `SeatActionModal.tsx` Start Session gate: `status === 'AVAILABLE' ||
  'ONLINE' || 'RESERVED'`.
- `frontend/src/types/seat.ts` — `SeatStatus` object lacks ONLINE (verified:
  only AVAILABLE…EXPIRED); add `ONLINE: 'ONLINE'` so the badge/card/modal
  types accept it.

### Affected existing tests

- `backend/tests/test_ws_manager.py` — `test_handle_register_sets_seat_online`
  asserts register → AVAILABLE; becomes ONLINE.
- `backend/tests/test_seat_status_integration.py` — register → AVAILABLE
  becomes ONLINE; cycle assertions updated.
- Any other test asserting register → AVAILABLE (grep during implementation:
  `test_ws_secret_db.py`, `test_ws_health_access.py`, integration fixtures).

## Section 2 — Backend: `enable_wake_on_lan` Flag (C.6)

- New entry in `DEFAULT_FEATURE_FLAGS` (`backend/core/bootstrap.py`):
  `"enable_wake_on_lan": "true"`. Reuses the existing settings-seeding path;
  admin-editable via the existing `PATCH /api/settings` → Feature Flags UI.
- `backend/services/wol_service.py:boot_all_seats`:
  - Return `[]` (log a debug line) when `not get_flag("enable_wake_on_lan")`.
  - Skip seats whose status is MAINTENANCE (never wake a broken PC); current
    "any seat with a MAC" behavior otherwise unchanged (at startup everything
    is OFFLINE, so the checklist's "all AVAILABLE seats" is satisfied).
- Startup call site (`backend/main.py:120`) unchanged — the gate lives inside
  `boot_all_seats` so the flag applies wherever it's invoked.

### Tests

- `trust the flag` on: seated MACs get packets → BOOTING (existing
  `test_boot_all_seats_sends_to_all_with_mac` keeps passing).
- Flag off: `boot_all_seats` sends nothing, seats stay as-is.
- MAINTENANCE seats skipped even when the flag is on.

## Section 3 — Backend: Downtime Tracking (C.11 / FR-SEAT-006)

### Schema

- Alembic migration: `seats.maintenance_since` (nullable `DateTime`, no index).
- `backend/models/seat.py` + `backend/schemas/seat.py` (`SeatBase`/`SeatResponse`):
  `maintenance_since: datetime | None`.
- `SeatResponse` additionally gains computed
  `maintenance_duration_seconds: float | None` = live `(now - maintenance_since)`
  when status is MAINTENANCE and the timestamp is set, else `None`
  (computed in `_seat_to_response`, seat_service.py; mirrors the existing
  `assigned_end_at` enrichment pattern).

### Service changes

- `set_maintenance` (seat_service.py:157): `seat.maintenance_since = now(UTC)`
  when the seat is **not** already MAINTENANCE (idempotent re-mark keeps the
  original timestamp; note is refreshed).
- `clear_maintenance` (line 198): `seat.maintenance_since = None`.
- `initialize_seat_statuses` (`backend/core/startup.py:101`) — **change**: skip
  seats whose status is MAINTENANCE (currently it flips *every* seat to
  OFFLINE, which would silently drop the maintenance flag and the timestamp on
  restart). Downtime therefore survives restarts. All other seats keep the
  existing OFFLINE reset.

### Tests

- `test_seat_service.py`: set → timestamp set; re-set → timestamp unchanged;
  clear → timestamp None; duration math; response carries both fields.
- `test_seat_router.py`: admin set/clear round-trip exposes the fields.
- `test_seat_status_integration.py`: MAINTENANCE seat survives
  `initialize_seat_statuses` (stays MAINTENANCE with `maintenance_since`
  intact); non-MAINTENANCE seats still reset to OFFLINE.

## Section 4 — Frontend: Maintenance UI (C.11)

`frontend/src/components/SeatActionModal.tsx` (Admin only; hidden for Cashier
via the existing `useAuthStore` role pattern):

- **Seat is MAINTENANCE:** "Clear Maintenance" button → `DELETE
  /api/seats/{id}/maintenance` (toast on success, modal stays open, seat flips
  live via WS). Status section shows `In maintenance since <local time>` plus a
  ticking `<duration>` (1 s interval while the modal is open; clear the
  interval on unmount).
- **Any other seat:** "Maintenance" opens an inline note field (small input +
  confirm, ESC/cancel to abort) → `PATCH /api/seats/{id}/maintenance
  {note}`.
- `frontend/src/api/seats.ts` gains `setMaintenance(id, note)` /
  `clearMaintenance(id)`; invalidates the seat query.
- **Vitest:** `SeatActionModal.test.tsx` — admin sees Maintenance on non-MAINT
  seats, note flow calls the API; MAINTENANCE seat shows Clear + the note and
  downtime line; cashier sees neither. `SeatStatusBadge.test.tsx` /
  `SeatCard.test.tsx` — ONLINE colors/labels. `SeatGrid.test.tsx` — ONLINE seat
  opens the action modal and can start a session.

## Section 5 — New Regression Tests (C.4, C.7, C.8)

New file `backend/tests/integration/test_c_recovery_sync.py`:

- **C.4 — pause excludes elapsed + sync:** start session via API; backdate
  `started_at`; pause; advance the pause; resume; assert
  `_compute_elapsed_seconds` excludes paused time; assert the agent received
  PAUSE/RESUME envelopes and the dashboard broadcasts carried PAUSED → IN_USE.
- **C.8 — agent crash recovery:** active session → `disconnect_agent` (seat →
  OFFLINE) → reconnect + REGISTER: seat **stays IN_USE** (regression for the
  clobber bug); send SYNC with drift >5 s → `ADOPT_ALE`; checkout bills the
  adopted elapsed; no double billing.
- **C.6 — WoL flag gating:** off → no packets/status change; on → packets to
  all MAC'd seats, MAINTENANCE excluded.

Also update `backend/tests/test_wol_service.py` (flag-gate unit tests) and
`backend/tests/integration/test_ac04_wol_packet.py` if the boot-send test needs
a flag seed (integration conftest sets flags explicitly where needed).

## Section 6 — C.1–C.11 Verification Run

Run in order after the code lands; failures follow the house fix-workflow
(reproduce → minimal fix → regression test → verify → record → check off).

- **C.1** — `test_ac01_ws_latency.py` (1 s gate; checklist's <100 ms verified
  manually: two dashboard tabs, start/pause/resume/checkout, no refresh).
- **C.2** — `test_seat_status_integration.py` + `test_ac04_wol_packet.py` +
  manual badge/zone walk-through of
  AVAILABLE → BOOTING → ONLINE → IN_USE → PAUSED → IN_USE → AVAILABLE,
  plus RESERVED and MAINTENANCE rendering.
- **C.3** — `test_sessions_router.py`, `test_session_service.py` (rate locked
  at start, walk-in + member).
- **C.4** — new C.4 test (Section 5) + `test_session_service.py` pause/resume.
- **C.5** — `test_ac02_api_performance.py`; optional Locust 50-agent run.
- **C.6** — `test_wol_service.py`, `test_ac04_wol_packet.py`, new flag tests;
  manual: toggle flag on, restart server, seats → BOOTING, agent in → ONLINE,
  none → UNREACHABLE.
- **C.7** — `test_ac07_sync_reconcile.py`; manual LAN-pull/reconnect on real
  hardware (server adopts max elapsed).
- **C.8** — new recovery test (Section 5); manual agent kill/restart on real
  hardware.
- **C.9** — `test_ac22_session_persistence.py`,
  `test_session_service.py::test_recover_active_sessions_on_restart`.
- **C.10** — `test_assigned_time_e2e.py`, `test_sweep_expired_sessions.py`.
- **C.11** — `test_seat_service.py` + new downtime tests + manual UI: mark
  out of order with note → badge, downtime line, session start 409; clear →
  AVAILABLE.
- `make lint` (ruff + mypy strict + ESLint + agent ESLint) after landing.

## Docs & Closeout

- `docs/api-reference.md`: add ONLINE row to the Seat Status Reference table
  ("Agent connected, seat idle").
- `docs/deployment.md` (+ operator guide where it lists flags):
  `enable_wake_on_lan` (default `true`, "WoL magic packets on server start").
- `docs/TODO.md`: mark C.1–C.11 `[x]`, add "Fixed during this pass" rows,
  update the project status line, commit.

## Out of Scope

- Dead "Checkout / Wake-on-LAN / View Health" buttons in `SeatActionModal`
  (belong to Sections D/H; SessionDrawer already covers checkout for in-use
  seats).
- Locust 50-agent run as a hard gate (optional validation tool).
- Any pricing/billing logic changes (Section D).
- Mobile owner view (Section K).
- TUYA console control (Section H).
