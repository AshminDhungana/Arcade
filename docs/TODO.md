# Arcade — Release Testing & Improvement Checklist

**Purpose:** Step-by-step, checkbox-driven checklist for engineers. Work top-to-bottom: test each feature area, fix any problem found (one at a time), verify the fix, then check off the item.

**Project status:** v1.0 released. All 23 acceptance criteria evaluated (15 verified, 8 deferred — see `docs/release/v1.0-acceptance-results.md`). The remaining work is full feature testing, fixing defects, and closing the deferred cross-platform items. **Sections 0, A, B and C are complete** (Section C as of commit `9232e73`) (Section B as of commit `6a92b03`) (Section 0 as of commit `92eb500`, Section A as of commit `7954502`) — testing of Sections D–M may begin.

## How to use this checklist

1. Complete **Section 0** (setup + baseline gates) first. Do not start testing until all gates pass.
2. Work through **Sections A–M in order**. Foundation areas (licensing, auth, sessions, billing) come first because later areas depend on them.
3. Every item is a concrete test scenario: **do this → expect that**. If the expectation fails, record the bug and fix it **before** moving on (see "Fix workflow" below).
4. Mark `[x]` only when the scenario passes with the verification command green.
5. When a section completes, **commit** and summarise in the git log what was tested and what was fixed.

## Running tests & linters

```bash
# Full test suite (backend + frontend) — the baseline
make test

# Linters: Python (ruff + mypy strict), frontend ESLint, agent ESLint
make lint

# Individual backend tests (use the venv interpreter, e.g. venv/Scripts/python)
python -m pytest backend/tests/<file>.py
python -m pytest backend/tests/integration/   # AC integration tests

# Individual frontend tests
cd frontend && npx vitest run <file>.test.tsx

# Launcher tests
python -m pytest tests/test_launcher_*.py tests/launcher/

# Build self-checks (launcher + agent)
python build.py --self-test

# Locust load testing (optional, for scale validation)
cd backend/tests/load && python seed_load_test.py   # see README.md
```

---

## Section 0 — Setup & Baseline Gates

Run these before any feature testing. If a gate fails, fix it first — everything below depends on these being green.

- [x] **0.1 Environment ready** — venv exists with `backend/requirements.txt` installed; `cd frontend && npm install` and `cd agent && npm install` complete.
- [x] **0.2 Backend test suite green** — `python -m pytest backend/` passes with 0 failures (ignore unrelated skips).
- [x] **0.3 Frontend test suite green** — `cd frontend && npm test -- --run` passes with 0 failures.
- [x] **0.4 Launcher tests green** — `python -m pytest tests/test_launcher_*.py tests/launcher/` passes.
- [x] **0.5 Python lint clean** — `ruff check backend/` and `mypy --strict backend/` produce no errors.
- [x] **0.6 Frontend lint clean** — `cd frontend && npm run lint` passes.
- [x] **0.7 Agent lint clean** — `cd agent && npm run lint` passes.
- [x] **0.8 Integration suite green** — `python -m pytest backend/tests/integration/` passes (AC-01 through AC-22).
- [x] **0.9 Build self-check** — `python build.py --self-test` reports launcher and agent self-checks passing.

**Done when:** gates 0.1–0.9 are all checked off and committed.

---

## Section A — Licensing, Launcher & Config

- [x] **A.1 Activation screen on fresh install** — delete `license.key` (and `arcade.config.json`); start `python launcher.py`. Verify: Activation screen appears, Hardware ID is displayed, no admin privileges required (uses `py-machineid`).
- [x] **A.2 Valid license activates** — activate with a key signed for this machine's HWID. Verify: setup wizard unlocks; `license.key` written; app proceeds to server start. Verify: `python -m pytest backend/tests/test_licensing.py backend/tests/test_keygen*.py`
- [x] **A.3 HWID mismatch rejected** — copy the same license to a different machine (or tamper with HWID sources). Verify: activation fails with a clear message, app stays on activation screen. Existing data (db, config) untouched.
- [x] **A.4 Corrupted/missing license** — corrupt `license.key` bytes. Verify: signature check fails, app returns to activation screen, no crash, no data corruption.
- [x] **A.5 Trial license expiry** — issue a trial license with past/future expiry. Verify: past-expiry rejected; valid trial proceeds.
- [x] **A.6 Launcher start/stop lifecycle** — Start server via Launcher → confirm toolbar/setup state → stop server. Verify uvicorn subprocess spawns and terminates cleanly.
- [x] **A.7 Exit while server running** — click Launcher "X" with server up. Verify: confirmation dialog appears; Yes stops server + exits; No keeps both running. Verify: `python -m pytest tests/test_launcher_ipc.py`
- [x] **A.8 Setup wizard persists config** — complete wizard (cafe name, zones, seats, printer). Verify: `arcade.config.json` written correctly; wizard re-run shows saved values; cafe name shown in agent overlay (see I.4).
- [x] **A.9 Launcher UI regression** — theme, motion, and widget modules render correctly (Windows). Verify: `python -m pytest tests/launcher/`

**Done when:** A.1–A.9 pass.

---

## Section B — Auth, Staff, Shifts & Audit

- [x] **B.1 Staff login** — create Admin + Cashier; log in with Staff ID + PIN. Verify: wrong PIN rejected; 5 failed attempts lock the account. Verify: `python -m pytest backend/tests/test_auth.py backend/tests/test_staff_auth.py backend/tests/test_auth_service.py`
- [x] **B.2 PIN hashing** — confirm stored PINs are Argon2id hashes (no plaintext in DB).
- [x] **B.3 Token revocation** — log in, change the PIN, then use the old JWT. Verify: the old token is rejected (token_version bump). Verify: `backend/tests/test_auth_service.py`
- [x] **B.4 Role permissions** — Cashier can bill + run POS but cannot: toggle feature flags, trigger force overlay, restore backups, manage staff, or see admin-only settings (expect 403s).
- [x] **B.5 Shift open** — open shift with cash float; dashboard shows running totals (revenue, sessions, avg duration).
- [x] **B.6 Shift close & reconciliation** — run mixed cash/card/package sessions, close shift with counted cash. Verify: expected cash vs variance computed; variance > `shift_cash_variance_threshold` flagged. Verify: `python -m pytest backend/tests/test_shift_service.py backend/tests/test_shifts_router.py backend/tests/integration/test_ac10_shift_reconciliation.py`
- [x] **B.7 Unprinted-invoice gate** — with `block_shift_close_unprinted` on, close a shift leaving a `FAILED`/`SKIPPED` invoice. Verify: warning/block per flag setting. Verify: `python -m pytest backend/tests/test_invoice_router_print_gate.py`
- [x] **B.8 Audit log completeness** — perform a representative set of sensitive ops (login, session start/checkout, shift close, remote restart, settings change, feature flag toggle, backup, license check). Verify: all appear in the audit log with staff id, timestamp, action, entity, detail. Verify: `python -m pytest backend/tests/test_audit.py backend/tests/integration/test_ac09_audit_immutability.py`
- [x] **B.9 Audit log immutability** — verify no update/delete routes exist for audit entries (checklist: no `PUT/DELETE /api/audit*`).

**Done when:** B.1–B.9 pass.

**2026-08-13 pass:** all B.1–B.9 verified — B.4 restore-backup 403 deferred to Section L (endpoint not yet implemented); B.5 verified via live-totals API + ShiftModal (revenue/sessions/avg duration). Verification tests: `test_pin_hashing.py`, `test_permissions_matrix.py`, `test_audit_completeness.py`, `test_audit_immutability_api.py`, `test_license_router.py`.

---

## Section C — Seats, Dashboard & Sessions

- [x] **C.1 Live seat grid** — open two dashboard tabs; start/pause/resume/checkout a seat. Verify: status changes propagate to both tabs in <100ms, no refresh. Verify: `python -m pytest backend/tests/integration/test_ac01_ws_latency.py`
- [x] **C.2 Seat status lifecycle** — exercise each state transition: AVAILABLE → BOOTING → ONLINE → IN_USE → PAUSED → IN_USE → AVAILABLE, plus RESERVED and MAINTENANCE. Verify badges/zones render correctly. Verify: `python -m pytest backend/tests/test_seat_status_integration.py backend/tests/integration/test_ac04_wol_packet.py`
- [x] **C.3 Session start flow** — start walk-in and member sessions; assign zone + rate; confirm billing starts at the locked rate. Verify: `python -m pytest backend/tests/test_sessions_router.py backend/tests/test_session_service.py`
- [x] **C.4 Pause/resume** — pause then resume a session; elapsed time excludes paused time; dashboard + agent stay in sync. Verify: `backend/tests/integration/test_c_recovery_sync.py::test_c4_pause_excludes_elapsed_and_syncs_agent`
- [x] **C.5 Session speed/perf** — start/end under 10s of staff interaction; 50 concurrent sessions all <1s API latency. Verify: `python -m pytest backend/tests/integration/test_ac02_api_performance.py`
- [x] **C.6 WoL boot** — enable `enable_wake_on_lan`; restart server. Verify: magic packet broadcast to all AVAILABLE seats, status → BOOTING, agent registers within 60s → ONLINE, else UNREACHABLE after watchdog. Verify: `python -m pytest backend/tests/test_wol_service.py backend/tests/integration/test_ac04_wol_packet.py`
- [x] **C.7 LAN-drop resilience** — pull the client's LAN cable 60s into a session, reconnect. Verify: billed time matches wall clock ±2s (server adopts max elapsed via SYNC). Verify: `python -m pytest backend/tests/integration/test_ac07_sync_reconcile.py backend/tests/test_session_service.py`
- [x] **C.8 Agent crash recovery** — kill the agent mid-session, restart it. Verify: session resumes with correct elapsed time, no double billing. Verify: `backend/tests/integration/test_c_recovery_sync.py::test_c8_agent_crash_recovery_bills_adopted_elapsed_once`
- [x] **C.9 Server restart recovery** — leave 5 sessions active, kill/restart the server. Verify: all sessions recover with correct elapsed time on the dashboard; agents re-sync. Verify: `python -m pytest backend/tests/integration/test_ac22_session_persistence.py backend/tests/test_session_service.py::test_recover_active_sessions_on_restart`
- [x] **C.10 Assigned-time limit** — with `enable_assigned_time_limit`, set a hard time limit; verify session ends at limit. Verify: `python -m pytest backend/tests/test_assigned_time_e2e.py backend/tests/test_sweep_expired_sessions.py`
- [x] **C.11 Maintenance mode** — mark a seat out of order with a note; verify badge, downtime tracking, and that sessions can't start on it. Verify: `test_seat_service.py` (maintenance_since + duration), `test_seat_router.py`, `test_startup.py::test_initialize_seat_statuses_preserves_maintenance`, `SeatActionModal.test.tsx` (note flow, Clear, downtime line).

**Done when:** C.1–C.11 pass.

**2026-08-13 pass:** all C.1–C.11 verified — C.1 (WS latency suite), C.2 (seat lifecycle + WoL packet suites), C.3 (sessions router/service), C.4/C.8 (new `test_c_recovery_sync.py`: pause excludes paused window, agent SHOW/HIDE_OVERLAY envelopes, crash-reconnect keeps IN_USE, ADOPT_ALE billed exactly once), C.5 (`test_ac02_api_performance.py`), C.6 (flag-gated boot + packet suite), C.7 (`test_ac07_sync_reconcile.py`), C.9 (`test_ac22_session_persistence.py`), C.10 (assigned-time e2e + sweep), C.11 (maintenance downtime tracking, startup survival, frontend note/Clear/downtime line). Full backend suite 1005 passed, frontend 354 passed, ruff + mypy strict + ESLint clean. Real-hardware steps (two-tab <100 ms, LAN pull, agent kill/restart, WoL restart) ride on RE-2's hardware walkthrough. Fixes landed in `9506695`, `30c0e75`, `9232e73`.

---

## Section D — Billing, Packages, Promotions & Vouchers

- [x] **D.1 Pricing models** — verify per-minute, flat hourly, time-block, peak/off-peak (via peak schedule), and device-type rates bill correctly. Verify: `python -m pytest backend/tests/test_billing_service.py backend/tests/test_billing_service_checkout.py backend/tests/test_peak_schedule_crud.py backend/tests/test_device_type_crud.py`
- [x] **D.2 Rate lock at session start** — change a zone rate mid-session; verify the running session keeps the original rate.
- [x] **D.3 Checkout math** — run a checkout with time + POS items + tax + promo. Verify: paise integer arithmetic, no rounding errors. Verify: `python -m pytest backend/tests/integration/test_ac03_checkout_full.py`
- [x] **D.4 Package drawdown + overflow** — member with a 30-min package plays 45 min. Verify: 30 min package + 15 min per-minute overflow billed correctly, atomically. Verify: `python -m pytest backend/tests/test_package_drawdown.py backend/tests/integration/test_ac11_package_drawdown.py`
- [x] **D.5 Package types** — hours, day pass (expires at midnight), night pass (22:00–06:00 window), monthly pass all enforce correctly; selling packages against wallet/cash works, insufficient wallet rejected. Verify: `python -m pytest backend/tests/test_package_service.py backend/tests/test_packages_router.py`
- [x] **D.6 Promotions** — happy hour, flash discount, first-visit, group, birthday apply correct percentages and zone restrictions. Verify: `python -m pytest backend/tests/test_promotion_service.py backend/tests/test_promotions_router.py`
- [x] **D.7 Voucher lifecycle** — generate voucher (with value), print, redeem once at counter, reject second use, reject unknown code. Verify: `python -m pytest backend/tests/test_voucher_service.py backend/tests/test_voucher_router.py`
- [x] **D.8 Atomic package updates** — two sessions drawing from the same package concurrently; verify no overspend (race test). Verify: `python -m pytest backend/tests/test_package_drawdown.py`
- [x] **D.9 Force-close checkout** — close a session without printing; verify `CHECKOUT_FORCED_UNPRINTED` audit entry and unprinted invoice flag set. Verify: `python -m pytest backend/tests/test_billing_service_force_close.py`

**Done when:** D.1–D.9 pass.

**2026-08-14 pass:** all D.1–D.9 verified — D.1 (pricing models incl. peak schedule + device-type CRUD), D.2 (new `test_rate_lock_mid_session_zone_change_keeps_original_rate` in `test_billing_service_checkout.py`; zone rate changed mid-session, checkout bills the locked rate), D.3 (`test_ac03_checkout_full.py`), D.4 (unit + AC-11 suites; stale node reference corrected — scenario lives in `test_package_drawdown.py::test_drawdown_with_overflow`), D.5 (package types incl. day/night/monthly windows + wallet/cash sale), D.6 (promotion percentages + zone restrictions), D.7 (voucher lifecycle incl. single-use), D.8 (new `test_concurrent_drawdown_no_overspend` in `test_package_drawdown.py`: two sessions drawdown the same entitlement concurrently via separate DB sessions — remaining never negative, aggregate billing deterministic; drawdown is a single atomic guarded UPDATE), D.9 (force-close `CHECKOUT_FORCED_UNPRINTED` audit + unprinted flag). Full backend suite 1007 passed (2 skipped), ruff + mypy strict clean. No defects found; 2 tests added, 1 stale reference corrected.

---

## Section E — POS, Menu, Inventory & Printing

- [ ] **E.1 POS flow** — add food/drink items to an active session tab; verify itemised rows, quantities, prices, and totals appear on checkout + receipt. Verify: `python -m pytest backend/tests/test_pos_service.py backend/tests/test_pos_router.py`
- [ ] **E.2 Menu management** — create/update/disable menu items; verify disabled items can't be sold. Verify: `python -m pytest backend/tests/test_menu_crud.py backend/tests/test_inventory_router.py`
- [ ] **E.3 Inventory levels** — sell below low-stock threshold → alert; hit zero → item auto-disabled as sold out. Verify: `python -m pytest backend/tests/test_inventory_service.py`
- [ ] **E.4 Restock log** — record a delivery with timestamp + quantity; verify stock rises and log entry exists.
- [ ] **E.5 Thermal printing** — print a real receipt on ESC/POS printer; verify all receipt fields (cafe name, seat, session times, duration, rate, package, promo, items, subtotal, tax, total, payment method, staff, invoice #). Verify: `python -m pytest backend/tests/test_print.py backend/tests/test_print_service_printer_uri.py`
- [ ] **E.6 PDF fallback** — print with no thermal printer configured; verify PDF/browser-print path works and contains the same fields.
- [ ] **E.7 Printer discovery/config** — discovery finds local printers; saving a printer URI persists and is used. Verify: `python -m pytest backend/tests/test_printer_discovery.py backend/tests/test_printers_api.py backend/tests/test_config_printer_uri.py`
- [ ] **E.8 Print queue / retry** — verify print job queue, `PRINT_RETRY` on failure, print-status gate behaviour, and scheduler release of blocked invoices. Verify: `python -m pytest backend/tests/test_print_job_model.py backend/tests/test_print_job_repo.py backend/tests/test_scheduler_print_release.py`

**Done when:** E.1–E.8 pass.

---

## Section F — Members & Wallets

- [ ] **F.1 Member CRUD** — create, update, deactivate a member from the dashboard; verify audit entries. Verify: `python -m pytest backend/tests/test_members_list.py backend/tests/test_member_service.py`
- [ ] **F.2 Wallet top-up** — add funds; verify integer-paise balance and ledger entries; purchase draws from wallet first. Verify: `python -m pytest backend/tests/test_wallet_ledger.py`
- [ ] **F.3 Loyalty points** — verify points accrue per spend and redeem correctly per tier rules.
- [ ] **F.4 Tier discounts** — members in higher tiers get the configured % discount at checkout.
- [ ] **F.5 Package purchase/redeem** — buy a package against a member; verify balance updates; redeem entries logged (`PACKAGE_REDEEM`). Verify: `backend/tests/test_package_service.py`

**Done when:** F.1–F.5 pass.

---

## Section G — Reservations

- [ ] **G.1 Create/cancel reservation** — reserve a seat for a future time/group; verify seat shows RESERVED in grid. Verify: `python -m pytest backend/tests/test_reservation_service.py backend/tests/test_reservation_router.py`
- [ ] **G.2 Reservation expiry/sweep** — expired unconfirmed reservations are released by the scheduler. Verify: `python -m pytest backend/tests/test_reservation_scheduler.py`
- [ ] **G.3 Conflict handling** — double-book the same seat/time; verify second reservation is rejected or queues per policy. Verify: `backend/tests/test_reservation_foundation.py`

**Done when:** G.1–G.3 pass.

---

## Section H — Remote Commands, PC Health & Consoles

- [ ] **H.1 Remote restart** — from SeatCard menu, restart an active PC; verify PC reboots, agent auto-starts, seat goes IN_USE → BOOTING → ONLINE; `REMOTE_RESTART` audit entry. Verify: `python -m pytest backend/tests/test_remote_commands.py backend/tests/test_remote_commands_router.py backend/tests/integration/test_ac06_remote_restart.py`
- [ ] **H.2 Remote shutdown** — shutdown a client; verify seat → UNREACHABLE after watchdog; manual power-on + WoL restores it.
- [ ] **H.3 Send message** — push a message; verify it appears on the client screen instantly.
- [ ] **H.4 Screenshot** — capture from dashboard; verify JPEG quality 80%, max 1280×720, no upscale, base64 over WS. Verify: `python -m pytest backend/tests/integration/test_ac18_screenshot_limits.py`
- [ ] **H.5 Screenshot rate-limit** — fire 10 rapid requests at one seat; verify only 1 processed, rest rejected/queued (429 semantics).
- [ ] **H.6 PC health** — verify CPU%, RAM%, temperature, disk reported every 60s and displayed on dashboard. Verify: `python -m pytest backend/tests/test_ws_health_access.py`
- [ ] **H.7 Console control (Tuya)** — with `enable_tuya_console_control` on, power a PS5/Xbox plug on/off; verify LAN-only control after pairing (no internet). Verify: `python -m pytest backend/tests/test_tuya_service.py backend/tests/test_tuya_router.py backend/tests/test_tuya_start_session.py backend/tests/test_tuya_checkout.py backend/tests/integration/test_ac16_tinytuya.py`
- [ ] **H.8 Feature-flag gating** — with `enable_remote_commands` off, remote actions are hidden/blocked.

**Done when:** H.1–H.8 pass.

---

## Section I — Agent Kiosk Overlay

- [ ] **I.1 Overlay on session start** — start a session; verify overlay hides, desktop accessible, branded splash shows ~5s (HIDE_OVERLAY). End session: overlay returns (SHOW_OVERLAY), seat AVAILABLE. Verify: `python -m pytest backend/tests/test_ws_agent_envelope.py`
- [ ] **I.2 Paused overlay** — pause a session; verify client shows the paused state/overlay; resume continues. With `overlay_pauses_billing` on, verify no time bills while paused.
- [ ] **I.3 Countdown + low-time warning** — at the configured warning (e.g. 5 min), verify countdown popup on client; verify `test_low_time_service.py` logic. Verify: `python -m pytest backend/tests/test_low_time_service.py`
- [ ] **I.4 Cafe name on overlay** — verify the overlay center shows the cafe name from setup, not "Arcade"; with no cafe name set, it falls back to "Arcade". (Regression: `docs/superpowers/specs/2026-08-09-kiosk-overlay-cafe-name-design.md`; run `cd agent && npx vitest run`.)
- [ ] **I.5 Call Staff button** — from a running session, trigger Call Staff; verify staff alert appears on the dashboard (`StaffAlertModal`), including from the OS-cursor hot zone.
- [ ] **I.6 Announcements** — push an announcement; verify it appears on all client screens instantly.
- [ ] **I.7 Kill-switch: force overlay** — with no active session, from the dashboard Commands tab force overlay ON; verify client locks; force overlay OFF unlocks. (Admin-only; Cashier must get 403.)
- [ ] **I.8 Commands tab remote controls** — with an active session, pause/resume the timer from the Commands tab; verify the seat drawer stays open and the button flips to Resume live. (Regression: `docs/superpowers/specs/2026-08-09-commands-tab-remote-controls-design.md`; frontend tests: `cd frontend && npx vitest run src/components/CommandsPanel.test.tsx`)
- [ ] **I.9 Bypass attempts (per shared checklist)** — work through `docs/checklists/AC-13_kiosk_overlay_manual_checklist.md`: Alt+F4, F12, Ctrl+P, Ctrl+Shift+I, F11, Escape, WinKey, Task Manager (Windows) / Cmd+Q/W/H/M (macOS) / Super, Alt+F4 (Linux X11). Confirm each documented known limitation (Ctrl+Alt+Del, Win+L, Cmd+Tab/Space, Force Quit, TTY switches, Wayland) behaves as documented — no *new* bypasses.
- [ ] **I.10 Session end → overlay restore** — force-quit the agent mid-session, restart it; verify overlay restores from local SQLite cache and SYNC reconciles (see C.8).
- [ ] **I.11 Multi-monitor & power events** — overlay spans primary (or all) monitors; sleep/wake and lid close/open restore the overlay.
- [ ] **I.12 Overlay branding regression** — brand display tests: `cd agent && npx vitest run`.
- [ ] **I.13 Self-provisioning (enroll code flow)** — on the dashboard open a seat → Enroll Code (admin); verify a one-time `ABCD-EFGH` code appears, valid 15 min, single-use. On the client, launch the agent first-run: verify it discovers the server via UDP beacon (or manual `server_url` fallback in the first-run window), accepts the code, receives `seat_id` + `agent_secret`, writes `agent.config.json`, and relaunches into the kiosk — no manual file copying. Verify: `python -m pytest backend/tests/test_enroll_routers.py backend/tests/test_enrollment_service.py`
- [ ] **I.14 Enroll code failures & expiry** — wrong code rejected; expired code rejected; already-consumed code rejected; code generation is Admin-only (Cashier → 403).
- [ ] **I.15 Staff override + master PIN** — during a session, open the agent's staff-override dialog and enter the staff override PIN; verify the kiosk drops and the PIN checks against the server. Verify the build-injected emergency master PIN (default `1928`, override with `MASTER_PIN`/`ARCADE_MASTER_PIN` at build time) works as a fallback and is never shown in the UI.
- [ ] **I.16 Agent re-enrollment** — from the agent's Settings button, re-open the first-run window and re-enroll with a new code; verify the old seat binding is replaced and `agent.config.json` is rewritten (`seat_id`/`agent_secret` updated).

**Done when:** I.1–I.16 pass on the primary platform (Windows), with documented results for Linux/macOS per Section M.

---

## Section J — Events & Tournaments

- [ ] **J.1 Event creation** — create an event with entry fee; verify eventbrite-style registration works. Verify: `python -m pytest backend/tests/test_events.py backend/tests/test_events_router.py backend/tests/test_event_service.py`
- [ ] **J.2 Participant registration + seats** — register participants, assign seats, charge entry fee (wallet or standalone). Verify: `backend/tests/test_events_e2e_smoke.py`
- [ ] **J.3 Brackets** — single and double elimination: advance winners, record results, compute prize pool.
- [ ] **J.4 Event billing** — verify entry fees hit member wallets or transactions correctly, page renders on dashboard. Verify: `cd frontend && npx vitest run src/pages/Events.test.tsx`

**Done when:** J.1–J.4 pass.

---

## Section K — Analytics & Reports

- [ ] **K.1 Dashboard analytics** — today's revenue, busiest hours, seat utilisation by zone, top POS items, member activity all populate correctly. Verify: `python -m pytest backend/tests/test_analytics.py backend/tests/test_analytics_indexes.py backend/tests/integration/test_ac05_analytics_fields.py`
- [ ] **K.2 Expense tracking** — log rent/electricity/restock/wages; verify gross vs net P&L estimate.
- [ ] **K.3 Shift reports** — per-shift revenue, sessions, avg duration, payment breakdown. Verify: `python -m pytest backend/tests/test_shifts_router.py backend/tests/test_schemas_invoice_shift.py`
- [ ] **K.4 Mobile owner view** — open `/mobile` on a phone on cafe WiFi; verify responsive cards: today's revenue, active sessions, shift summary, top zones; real-time updates without refresh.

**Done when:** K.1–K.4 pass.

---

## Section L — Backups, Restore & Feature Flags

- [ ] **L.1 Nightly backup** — APScheduler cron at 03:00 runs SQLite `.backup()`; verify timestamped file in `backups/` with SHA256 manifest. Verify: `python -m pytest backend/tests/test_backup.py backend/tests/test_backup_router.py backend/tests/integration/test_ac20_backup_scheduler.py`
- [ ] **L.2 Retention** — simulate 35 days; verify files older than `backup_retention_days` (default 30) auto-deleted.
- [ ] **L.3 Manual backup** — `POST /api/admin/backup` (Admin only) creates a backup on demand.
- [ ] **L.4 Restore** — `POST /api/admin/restore` stops server, replaces DB, restarts; verify data integrity after restore.
- [ ] **L.5 All 23 feature flags** — toggle each flag in Settings (and via API); verify UI hides/shows correctly and endpoints enforce guards. See `docs/deployment.md` Appendix B for the flag list. Verify: `python -m pytest backend/tests/test_feature_flags.py backend/tests/integration/test_ac08_feature_flags.py`
- [ ] **L.6 Daily-ops sanity** — after restore, verify sessions, dashboard, and agent sync all still work (no schema drift). Verify: `python -m pytest backend/tests/test_bootstrap.py backend/tests/test_db_bootstrap.py`

**Done when:** L.1–L.6 pass.

---

## Section M — Cross-Platform Deferred Items

These were DEFERRED in `docs/release/v1.0-acceptance-results.md`. Close them out one by one; each needs real-hardware verification.

- [ ] **M.1 Restore macOS platform service** — resurrect `agent/src/main/platform/macos.ts` from orphaned commit `54256ca` (kiosk overlay, restart, shutdown, screenshot); merge to `main`, wire into `platform/index.ts`, add tests in the agent test suite.
- [ ] **M.2 macOS kiosk overlay verified (AC-13/17)** — on a physical Mac: overlay displays, Cmd+Q/W/H/M blocked, screen-recording permission for screenshots granted; document remaining OS-protected shortcuts (Cmd+Tab, Cmd+Space, Force Quit) as known limitations in `docs/agent-setup.md`.
- [ ] **M.3 macOS remote commands verified (AC-14)** — restart/shutdown via `osascript`; document `sudoers` requirement (`arcade-agent ALL=(ALL) NOPASSWD: /sbin/shutdown`).
- [ ] **M.4 macOS launcher verified (AC-15)** — PyInstaller `--onedir` build on a Mac (`brew install python-tk`); Tkinter launcher + uvicorn subprocess run correctly.
- [ ] **M.5 Linux Wayland kiosk verified (AC-13)** — test GNOME (Wayland) and KDE (Wayland); document compositor quirks; confirm X11 fallback works as documented deployment requirement (Cage, gnome-kiosk, ubuntu-frame).
- [ ] **M.6 Agent auto-start on all OSes** — systemd service (Linux), LaunchAgent (macOS), startup entry / service (Windows) — verify agent starts on boot and reconnects. See `docs/autostart/`.

**Done when:** M.1–M.6 verified on real hardware, or explicitly re-scoped with justification in the acceptance-results doc.

---

## Fix workflow (for any failing item)

When an item fails, follow this loop **before** moving to the next item:

1. **Reproduce** — capture exact steps, logs (`uvicorn` output, agent console, browser console), and screenshots.
2. **Minimal fix** — change the smallest amount of code that fixes the root cause. Follow existing patterns in the affected module. Do not broaden scope.
3. **Add a regression test** — a failing test first (backend pytest or frontend vitest, matching the module's existing suite).
4. **Verify** — run the affected test file(s) + the linters (`make lint`).
5. **Record** — add a line under "Fixed during this pass" below, and reference the fix commit.
6. **Check off** — only after all verification above is green.

## Fixed during this pass

| Date | Area | Item | Problem found | Fix commit |
|------|------|------|---------------|------------|
| 2026-08-13 | C.8 | SYNC reconciliation | `_handle_sync` returned `ADOPT_ALE` but never persisted the adopted elapsed — checkout billed the stale server anchor (spec §5 requires billing the adopted elapsed). | `9506695` |
| 2026-08-13 | B.9 | audit API test | `test_audit_routes_are_read_only` failed: FastAPI 0.138 mounts included routers as `_IncludedRouter`, so `app.routes` no longer exposes flattened `/api/audit` routes; test now walks included routers. | `9506695` |
| 2026-08-13 | C.11 | maintenance downtime | `initialize_seat_statuses` flipped every seat to OFFLINE at startup, silently dropping MAINTENANCE status + `maintenance_since` on restarts; now skips MAINTENANCE seats (spec §3). | `9506695`, `30c0e75` |
| 2026-08-12 | Setup gates | 0.3 | Node 22+ experimental `localStorage` shadowed jsdom's in vitest (vitest-dev/vitest#10867), breaking 13 frontend tests | `92eb500` |
| 2026-08-12 | Setup gates | 0.4 | `launcher.py` only accepted the `self-test` subcommand, but build.py/CI/tests invoke `--self-test` as a flag | `92eb500` |
| 2026-08-12 | Setup gates | 0.5 | ruff UP047: `_with_retry` should use PEP 695 type parameters | `92eb500` |
| 2026-08-12 | Setup gates | 0.9 | build.py ran agent smoke-test against the NSIS installer, which doesn't understand `--smoke-test`; now targets `win-unpacked/Arcade Agent.exe` | `92eb500` |
| 2026-08-12 | Section A | A.1–A.9 | None found — all items passed on first run; tested against packaged `dist/Arcade Launcher.exe` (wizard writes config/db into `dist/`), tampered keys generated via `tools/keygen` | — |
| 2026-08-13 | Section B | B.1–B.9 | Full pass: 118 Section-B tests + full backend suite (1000) + frontend (344) green, lint clean. Fixed during pass: license-check endpoint was missing (`POST /api/license/verify` + `LICENSE_CHECK` audit, Task 4); settings PATCH didn't audit → `SETTINGS_CHANGED`; live shift totals + variance threshold shipped. B.4 restore-backup 403 deferred to Section L (endpoint not yet implemented); B.5 verified via live-totals API + ShiftModal. See `d28212e`–`807ab78` | `6a92b03` |

---

## Final Re-verify & Closeout

- [ ] **RE-1** — `make test` and `make lint` fully green (all suites).
- [ ] **RE-2** — One full end-to-end walkthrough per **Customer Flows** in `README.md` (walk-in, member with package, group reservation) on real hardware.
- [ ] **RE-3** — `python build.py --self-test` green; a release build (Windows at minimum) launches and passes the Section 0 gates.
- [ ] **RE-4** — `docs/release/v1.0-acceptance-results.md` updated: remaining DEFERRED items either verified or re-justified; sign-off table filled.
- [ ] **RE-5** — This checklist has no unchecked items (or explicitly re-scoped ones with justification).

## Known limitations (not bugs — do not "fix")

| Limitation | Platform |
|---|---|
| Ctrl+Alt+Del, Win+L | Windows |
| Cmd+Tab, Cmd+Space, Cmd+Opt+Esc (Force Quit) | macOS |
| TTY switching (Ctrl+Alt+F1–F7) | Linux |
| Wayland always-on-top quirks | Linux (Wayland) |
| Offline session start (all sessions started from dashboard) | All |
| Hardware changes need manual license reissue | All |

Full details: `docs/checklists/AC-13_kiosk_overlay_manual_checklist.md`, `docs/agent-setup.md`, `docs/release/v1.0-acceptance-results.md`.
