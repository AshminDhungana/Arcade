# Section C — Seats, Dashboard & Sessions: Implementation Plan

- Date: 2026-08-13
- Status: Approved — ready to execute
- Spec: `docs/superpowers/specs/2026-08-13-section-c-seats-dashboard-sessions-design.md`
- Workflow: TDD per house rules — failing tests first, then implementation, then targeted run, then full suite. Failures follow the house fix-workflow.
- Closeout: mark the Section C checklist items done in `docs/qa/checklists/section-c.md`, record fixes in the fixed-during-pass table, and commit.

## Verified facts (checked 2026-08-13, trust these)

- `backend/core/ws_manager.py` — `_handle_register` (~lines 355-403) sets
  `seat.status = AVAILABLE` unconditionally on REGISTER; `disconnect_agent`
  (~lines 229-240) sets OFFLINE unconditionally; local imports
  (`from backend.repositories import ...`) are the file's style; `session_repo`
  is imported locally inside `_handle_sync` (line 429); `SessionStatus` also
  imported locally there (~line 428).
- `backend/services/session_service.py` — `start_session` gate at line ~181
  rejects anything not AVAILABLE/RESERVED; session-expiry code uses EXPIRED.
- `backend/services/reservation_service.py` — reserve gate at line ~305.
- `backend/services/remote_command_service.py` — bulk idle-seat targets at
  line ~437 (AVAILABLE + ONLINE after change).
- `backend/services/wol_service.py` — `wol_success_callback` (~line 299) sets
  seat AVAILABLE; `boot_all_seats` (~line 247); `zone_and_seat_with_mac` /
  `zone_and_seat_no_mac` fixtures already exist in `test_wol_service.py`.
- `backend/repositories/seat_repo.py` — `create` starts seats OFFLINE;
  `on_registered` resets `overlay_forced`/`agent_version`.
- Unit fixtures (`backend/tests`): `db`, `zone_and_seat` → `(zone, seat)`,
  `admin_staff`, `staff_member` (each file defines its own).
- Integration fixtures (`backend/tests/integration/conftest.py`): `integration_db`,
  `seeded_zone`, `seeded_seat`, `admin_staff`, `integration_client`;
  `auth_headers(staff_id=..., role=...)` from `integration/utils.py`.
- API shapes (per `test_ac02_api_performance.py`, `test_ac22_session_persistence.py`):
  - Start: `POST /api/sessions` `{"seat_id": ...}` → 201, `id`.
  - Checkout: `POST /api/sessions/{id}/checkout` `{"payment_method": "CASH"}` →
    JSON with `time_charge_paise`, `total_paise`.
  - Agent connect in tests: set `seeded_seat.agent_secret = "test-secret"` and
    commit **before** `ws_manager.connect_agent(seat_id, "test-secret", mock_ws)`;
    patch `_start_heartbeat` with `patch.object(ws_manager, "_start_heartbeat", new=AsyncMock())`.
  - SYNC/ADOPT_ALE contract: see `test_ac07_sync_reconcile.py` (drift > 5 s → `ADOPT_ALE`).
- Frontend: `SeatStatusBadge.tsx` + `SeatCard.tsx` status maps lack ONLINE;
  `SeatActionModal.tsx` start gate is `status === 'AVAILABLE' || 'RESERVED'`;
  `frontend/src/types/seat.ts` `SeatStatus` object lacks ONLINE.
- Invoice service entry used by integrations: `billing_service.checkout_session(...)`.

## Task 1 — Backend: real ONLINE + session-aware REGISTER (ws_manager)

**Goal:** REGISTER puts idle agents ONLINE (not AVAILABLE), never clobbers
live states, and restores IN_USE/PAUSED after an agent crash (spec §1, C.8).
`backend/tests/integration/test_seat_status_integration.py` updated in place.

1. **Tests first** — update `test_seat_status_integration.py`:
   - Register path now asserts ONLINE where it asserted AVAILABLE.
   - New case: seat with an **active session** (start via `POST /api/sessions`
     with `integration_client`) → agent connect + `_handle_register` → seat
     stays **IN_USE**, not ONLINE. (This is the C.8 clobber regression.)
   - New case: seat seeded RESERVED → REGISTER → stays RESERVED.
   - New case: seat seeded MAINTENANCE → REGISTER → stays MAINTENANCE.
   - Keep the disconnect → OFFLINE assertion.
2. **Implement** in `_handle_register` — replace the unconditional AVAILABLE set:

```python
from backend.models import SessionStatus  # existing local-import style
...
if seat.status != SeatStatus.AVAILABLE:
    from backend.repositories import seat_repo, session_repo  # local import
    active = await session_repo.get_active_by_seat(db, seat.id)
    if active is not None:
        seat.status = (
            SeatStatus.PAUSED
            if active.status == SessionStatus.PAUSED
            else SeatStatus.IN_USE
        )
    else:
        seat.status = SeatStatus.ONLINE
else:
    seat.status = SeatStatus.ONLINE
```

   Keep: `overlay_forced` re-push, `wol_success_callback` firing, broadcast,
   heartbeat start, REGISTER_ACK. Update the file's docstring to the cycle
   OFFLINE → ONLINE → IN_USE → PAUSED → IN_USE → AVAILABLE.
3. **Verify** — `python -m pytest backend/tests/integration/test_seat_status_integration.py -q`, then full `python -m pytest backend/tests -q`.

## Task 2 — Gates accept ONLINE + WoL callback consistency

**Goal:** ONLINE is a startable/idle state everywhere; `wol_success_callback`
no longer mislabels BOOTING→AVAILABLE (spec §1 gates list).

1. **Tests first**:
   - `backend/tests/test_session_service.py` — ONLINE seat → `start_session`
     succeeds → IN_USE; existing fail cases (IN_USE/PAUSED/EXPIRED) untouched.
   - `backend/tests/test_reservation_service.py` — ONLINE seat can be reserved.
   - `backend/tests/test_remote_commands.py` — bulk targets include ONLINE+AVAILABLE, exclude IN_USE.
   - `backend/tests/test_wol_service.py` — `wol_success_callback` on a BOOTING
     seat → status ONLINE (was AVAILABLE).
2. **Implement**:
   - `session_service.py:181` gate → `not in (AVAILABLE, ONLINE, RESERVED)`.
   - `reservation_service.py:305` → `not in (AVAILABLE, ONLINE)`.
   - `remote_command_service.py:437` → `status in (AVAILABLE, ONLINE)`.
   - `wol_service.py:299` `wol_success_callback` → `SeatStatus.ONLINE`.
3. **Verify** — run the four test files, then the full suite.

## Task 3 — Frontend: render ONLINE (spec §1 frontend)

1. **Tests first** (`frontend` runs: `npm run vitest -- run <files>`):
   - `SeatStatusBadge.test.tsx` — ONLINE renders teal, "Online".
   - `SeatCard.test.tsx` — ONLINE card uses online colors/label.
   - `SeatActionModal.test.tsx` — ONLINE seat can start a session.
2. **Implement**:
   - `src/types/seat.ts` — add `ONLINE: 'ONLINE'` to `SeatStatus`.
   - `SeatStatusBadge.tsx` / `SeatCard.tsx` — add ONLINE (teal
     `bg-teal-500`/`border-l-teal-500`, label "Online").
   - `SeatActionModal.tsx` — start gate `status === 'AVAILABLE' || 'ONLINE' || 'RESERVED'`.
   - Grep `SeatStatus` in `src/` for stragglers (only types/components expected).
3. **Verify** — vitest targeted, then full `npm run vitest -- run` + lint
   (`npm run lint` or house equivalent).

## Task 4 — WoL flag gating (C.6, spec §2)

1. **Tests first** — `backend/tests/test_wol_service.py`:
   - Flag off → `boot_all_seats` sends no packets and changes no status.
   - Flag on → packets to all MAC'd seats; MAINTENANCE seats excluded.
   - `boot_single_seat` on a MAINTENANCE seat → skipped, logged, no packet.
   - Existing tests adjusted to seed the flag ON (settings fixture), per spec §5.
2. **Implement** — `backend/services/wol_service.py`:
   - `boot_all_seats`: read flag `enable_wake_on_lan` first; off → log + return.
   - Single/seeded boot paths: skip seats with `status == MAINTENANCE` (log).
3. **Verify** — `test_wol_service.py` + `test_ac04_wol_packet.py`, then full suite.

## Task 5 — DB: maintenance timestamps (C.5, spec §3)

1. **Inspect first** — grep `maintenance_started_at|maintenance_note` across
   `backend/` and `frontend/src/`; adjust names to local conventions if the
   grep finds existing partial references.
2. **Tests first** — `backend/tests/test_seat_service.py` (fixtures `db`,
   `zone_and_seat`, `admin_staff`):
   - `set_maintenance` sets `maintenance_started_at` + note, status MAINTENANCE.
   - `clear_maintenance` sets `maintenance_cleared_at`, clears note, AVAILABLE.
   - `_seat_to_response` includes the three fields.
3. **Implement**:
   - `backend/models/seat.py` — add `maintenance_started_at` /
     `maintenance_cleared_at` (DateTime(timezone=True), nullable),
     `maintenance_note` (String, nullable).
   - `backend/models/_timestamps.py` — register the two DateTime columns in
     `TIMESTAMP_COLUMNS` (check the file's exact mechanism while editing).
   - `backend/services/seat_service.py` — `set_maintenance` writes started_at +
     note; `clear_maintenance` writes cleared_at + clears note; replace
     `_seat_to_response` so it timezone-normalizes the two new fields via
     `_ensure_tz` (existing zone_name enrichment unchanged).
   - `backend/schemas/seat.py` `SeatResponse` — add the three fields.
4. **Verify** — `test_seat_service.py`, then full suite (watch `test_repositories.py` for schema ripples).

## Task 6 — Startup reset of stale maintenance (spec §3 notes)

- **Test first** — `backend/tests/test_seat_service.py`: startup pass over a
  MAINTENANCE seat with timestamps → status AVAILABLE + `maintenance_cleared_at`
  set (audit trail preserved).
- **Implement** — the startup seat-sync function (same one that flips OFFLINE
  at boot): when it meets MAINTENANCE, set cleared_at + flip AVAILABLE, log.
- **Verify** — targeted file, then full suite.

## Task 7 — Frontend: maintenance note + timestamps (C.5, spec §4)

1. **Tests first** (`frontend/src/components/`):
   - `SeatActionModal.test.tsx` — MAINTENANCE mode: note prefilled, Save posts
     it, Cancel resets form mode.
   - New `SeatMaintenanceFields.test.tsx` — note textarea, disabled while
     submitting, renders "Started …"/"Cleared …" when timestamps present.
2. **Implement**:
   - `SeatMaintenanceFields.tsx` (or inline fields in `SeatActionModal.tsx`) —
     note textarea + timestamp display.
   - `SeatActionModal.tsx` MAINTENANCE mode uses the note field; Save PATCHes
     `maintenance_note`; Cancel resets mode.
   - API client `set_maintenance` — accept `maintenance_note`.
3. **Verify** — vitest targeted + full, then lint.

## Task 8 — Integration regressions: C.8 crash recovery + C.4 pause sync

**New file** `backend/tests/integration/test_c_recovery_sync.py` (spec §5).
Fixtures: `integration_db`, `seeded_zone`, `seeded_seat`, `seeded_staff` /
`admin_staff`, `integration_client`, `auth_headers`.

- **C.8 — agent crash recovery:**
  1. `POST /api/sessions` (`{"seat_id": seeded_seat.id}`) → 201; seat IN_USE.
  2. Seed secret (`agent_secret = "test-secret"`, commit) **then**
     `connect_agent(seat.id, "test-secret", mock_ws)` (heartbeat patched);
     `disconnect_agent(seat.id)` → seat OFFLINE.
  3. Reconnect + `ws_manager._handle_register(seat.id)` → seat must be
     **IN_USE** (spec §1 session-aware row — fails if the clobber regresses).
  4. Backdate session `started_at` by 300 s; send a SYNC envelope per the
     `test_ac07_sync_reconcile.py` contract with a local elapsed that differs
     by > 5 s → assert `ADOPT_ALE` response; then checkout
     (`POST /api/sessions/{id}/checkout`) → `time_charge_paise` matches the
     adopted elapsed (±2 s) and there is one invoice only (no double billing).
- **C.4 — pause excludes elapsed + sync:** start session; backdate `started_at`;
  pause via API → the PAUSE envelope reaches the agent (`mock_ws.send` captured);
  resume → dashboard broadcast carries PAUSED → IN_USE; `_compute_elapsed_seconds`
  excludes the paused window (assert via a direct call with a known pause span).

- **Verify:** run the new file + full suite.

## Task 9 — Verification run + docs + closeout (spec §6)

1. Run the C.1–C.11 items in order (C.1 `test_ac01_ws_latency.py`, C.2 seat
   status file + WOL packet suite, C.3 manual WoL-only, C.4/C.6/C.8 via
   Task 8's new file, C.5 via Tasks 5/7, C.7 manual LAN-drop with the
   `test_ac07_sync_reconcile.py` suite, C.9–C.11 existing suites). Failures →
   house fix-workflow, then re-verify.
2. Docs: add ONLINE row to the Seat Status Reference table in
   `docs/api-reference.md`; add `enable_wake_on_lan` to `docs/deployment.md`
   (flag description, default off); check off the checklist file
   `docs/qa/checklists/section-c.md`; record anything fixed during the pass in
   the fixed-during-pass table (same file as Section B used).
3. Manual smoke: start backend + frontend; agent connects → ONLINE badge;
   start session → IN_USE; agent kill → OFFLINE; agent restart → IN_USE with
   running timer.

## Risks / open questions

- **EXPIRED edge**: an expired-limits seat whose agent reconnects maps to IN_USE
  (session still ACTIVE) until the sweep ends it — acceptable, matches C.8 flow.
- **AC-07 wording**: SDK checklist says disconnect shows UNREACHABLE, but the
  code and tests model OFFLINE on disconnect. Out of Section C scope; noted, not changed.
- **Migration**: additive nullable columns — no data backfill needed.
- **SDK/agent**: 2.8.0 released (agent already sends REGISTER on every
  connect); flag toggling is a manual backend/DB step.
- **Frontend model/timer**: ONLINE may briefly show a zero timer on the modal —
  dashboards show the mode label ("Ready"/"Online"), not a timer value for idle states (verify while implementing Task 3).

## Exit criteria

- All Task 1–8 tests pass; full backend suite green; frontend vitest + lint green.
- C.4, C.5, C.6, C.8 checkable as green in the Section C checklist; C.7 manual
  verified or explicitly carried forward.
- Docs updated (api-reference, deployment, checklist + fixed-during-pass).
