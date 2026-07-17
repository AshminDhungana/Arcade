# Epic 6.5.3: Overlay ↔ Timer Coupling — Design Spec

- **Date:** 2026-07-17
- **Phase:** 6.5 (Session Integrity, Owner Overlay Control & Assigned-Time Enforcement)
- **Owner track:** ENG-A (backend) + ENG-B (agent)
- **Status:** Design approved, pending implementation plan
- **Parent epic:** `docs/TODO.md` → Phase 6.5 → Epic 6.5.3

## 1. Overview

Epic 6.5.3 closes two gaps in the live product:

1. **Pause‑accounting coupling.** `RemoteCommandService.force_overlay()` (added in Epic 6.5.2) currently only flips `overlay_forced` and sends `FORCE_OVERLAY_ON/OFF` — it never touches session/billing state. The result is that forcing the overlay on a seat with an active session blocks the screen but keeps billing running, and there are now *two* unrelated ways to put a session into a billed‑pause state. This epic unifies forced overlay with the existing `pause_session()`/`resume_session()` accounting so there is exactly one source of truth for paused‑time math.
2. **Dead HUD timer channel.** The agent already has an `overlay:timer` IPC channel (`platform.updateTimer()`) and a `windows.ts` method that sends it, but **nothing ever calls `updateTimer()`**. The in‑game HUD countdown never ticks. This epic wires the agent's existing 10s session‑elapsed cadence into that channel so the countdown ticks. This is also required plumbing for Epic 6.5.4's expiry countdown.

## 2. Goals

- `force_overlay(show=True)` on a seat with an **ACTIVE** session transitions that session to **PAUSED** using the *same* accrual helpers as `pause_session()`, when the `overlay_pauses_billing` feature flag is on.
- `force_overlay(show=False)` accrues `total_paused_seconds` and returns the session to **ACTIVE** (the "always resume on force‑off" decision — see §6), reusing the same helpers as `resume_session()`.
- `total_paused_seconds` accrual lives in exactly two functions, used by both normal and forced flows — verified identical by a parity test.
- The behaviour is config‑driven via `overlay_pauses_billing` (default `true`); when `false` (an "Overtime"‑style mode some cyber‑cafe platforms support), `force_overlay` is pure lock control and never touches billing.
- The in‑game HUD countdown ticks, driven locally by the agent's existing 10s cadence (survives LAN drops; no server push).

## 3. Non‑Goals (explicitly out of scope)

- **Epic 6.5.4** owns `assigned_end_at`, the `EXPIRED` seat status, the expiry sweep, the extend endpoint, and the expiry countdown *rendering*. This epic only lays the agent‑side plumbing (a structured `overlay:timer` payload) that 6.5.4 will extend. It does **not** add `assigned_end_at` or render a countdown‑to‑expiry.
- No new WebSocket message *types*. `FORCE_OVERLAY_ON`/`FORCE_OVERLAY_OFF` already exist (Epic 6.5.2). We only enrich the `FORCE_OVERLAY_ON` **payload**.
- No new DB columns. We deliberately chose "always resume on force‑off" (§6) to avoid a `paused_by_overlay` column.
- The server does **not** gain a per‑session timer push loop. (The Epic 5.5 known‑gap note that says "the server does not yet push a live `overlay:timer`" is superseded by this agent‑local approach, which matches the Epic 6.5.3 task wording: "piggybacking on the existing `updateElapsed()` cadence in `ws/client.ts`".)

## 4. Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │  RemoteCommandService.force_overlay()        │
                    │  (backend/services/remote_command_service.py) │
                    └───────────────┬─────────────────────────────┘
                                    │ imports
                                    ▼
                    ┌─────────────────────────────────────────────┐
                    │  session_service._begin_pause() /             │
                    │  _accrue_pause()  ◄── also used by          │
                    │  pause_session() / resume_session()          │
                    └───────────────┬─────────────────────────────┘
                                    │ DB state + WS
              ┌─────────────────────┴──────────────────────┐
              ▼                                              ▼
   FORCE_OVERLAY_ON {session_id,started_at}      seat.status=PAUSED/IN_USE
   FORCE_OVERLAY_OFF  (via ws_manager)           (broadcast seat_updated)
              │
              ▼  agent WS client (agent/src/main/ws/client.ts)
   ┌──────────────────────────────────────────────┐
   │  startElapsedTimer() 10s callback:           │
   │   store.updateElapsed(...)                   │
   │   this.updateTimer({ elapsedSeconds })  ◄── NEW
   └───────────────────┬──────────────────────────┘
                        │ webContents.send('overlay:timer', ...)
                        ▼
              agent HUD (renderer/hud.ts)  ← countdown ticks
```

Two cooperating components, each changed minimally:
- **Backend (`session_service` + `remote_command_service`):** extract + reuse pause‑accounting helpers; make `force_overlay` call them behind the `overlay_pauses_billing` flag.
- **Agent (`ws/client.ts` + IPC plumbing):** a one‑line fan‑out in the existing 10s timer to drive the already‑present `overlay:timer` channel with structured data.

## 5. Components & Changes

### 5.1 Backend — shared pause‑accounting helpers (`backend/services/session_service.py`)

Add two module‑level helpers. They are pure state transitions on the ORM object (no WS, no audit, no seat broadcast) so they can be composed by both normal and forced flows.

```python
def _begin_pause(session: GamingSession, now: datetime) -> None:
    """Record pause start. No-op unless the session is ACTIVE.

    Guards against double-pause: a session already PAUSED keeps its
    original paused_at (e.g. forced overlay on a manually-paused seat).
    """
    if session.status != SessionStatus.ACTIVE:
        return
    session.status = SessionStatus.PAUSED
    session.paused_at = now


def _accrue_pause(session: GamingSession, now: datetime) -> None:
    """Add (now - paused_at) to total_paused_seconds; clear paused_at.

    No-op if paused_at is already None (nothing to accrue).
    """
    paused_at = _ensure_tz(session.paused_at)
    if paused_at is None:
        return
    duration = (now - paused_at).total_seconds()
    session.total_paused_seconds = (session.total_paused_seconds or 0) + int(duration)
    session.paused_at = None
```

Then refactor:
- `pause_session()` (lines ~256‑258): replace the inline `session.status = PAUSED; session.paused_at = ...` with `_begin_pause(session, datetime.now(UTC))`.
- `resume_session()` (lines ~322‑329): replace the inline accrual block with `_accrue_pause(session, datetime.now(UTC))`.

Net effect: the only place `paused_at` is written/read for accrual is these two helpers.

### 5.2 Backend — `force_overlay` pause coupling (`backend/services/remote_command_service.py`)

`force_overlay()` keeps its current skeleton (look up seat → send agent command → `set_overlay_forced` → audit). It gains session‑state management behind the flag. It imports the §5.1 helpers from `session_service` (`from backend.services import session_service` — no import cycle: `session_service` imports `audit_service`/`billing_service`/`promotion_service`, never `remote_command_service`; `remote_command_service` already imports `seat_service`).

Locate the active session with `session_repo.get_active_by_seat(db, seat_id)` (returns ACTIVE or PAUSED).

**`show=True`:**
1. If `get_flag("overlay_pauses_billing")` is **true** AND the session's status is **ACTIVE**:
   - `session_service._begin_pause(session, datetime.now(UTC))`
   - `await session_repo.update(db, session)`
   - set `seat.status = SeatStatus.PAUSED`; `await seat_repo.update(db, seat)`; broadcast `seat_updated` (same payload shape as `pause_session`).
   - (If the session is already PAUSED, or the flag is false: skip — pure lock. `_begin_pause` would no‑op anyway, but we also skip the seat/DB churn.)
2. Always:
   - `await seat_service.set_overlay_forced(db, seat_id, True)`
   - send `FORCE_OVERLAY_ON` with payload `{"session_id": session.id, "started_at": session.started_at_iso}` **when a session exists on the seat** (currently the payload is `{}` — change this so the agent preserves session/HUD context). When no session, send `{}`.
   - audit `OVERLAY_FORCED_ON` (unchanged).

**`show=False`:**
1. Always:
   - `await seat_service.set_overlay_forced(db, seat_id, False)`
   - send `FORCE_OVERLAY_OFF` (payload `{}`). On the agent, `hideKioskOverlay()` sets `sessionActive = true` and shows the HUD — so HUD context is restored with no extra `HIDE_OVERLAY` needed.
2. If `get_flag("overlay_pauses_billing")` is **true** AND a **PAUSED** session is on the seat (the session found in step 1 of the `show=True` path, or re‑queried):
   - `session_service._accrue_pause(session, datetime.now(UTC))`
   - `session.status = SessionStatus.ACTIVE`; `await session_repo.update(db, session)`
   - `seat.status = SeatStatus.IN_USE`; `await seat_repo.update(db, seat)`; broadcast `seat_updated`.
   - (Per the "always resume on force‑off" decision, this resumes a manually‑paused session too — documented as a known limitation in §7.)

`bulk_force_overlay()` (lines ~327‑351) requires **no change** — it simply loops `force_overlay()` and inherits the new behaviour.

### 5.3 Feature flag default (`backend/scripts/seed_dev.py`)

`overlay_pauses_billing` is documented `true` in Appendix D, but `core/feature_flags.get_flag()` returns `False` for any unknown key (defensive default). Therefore the flag **must be seeded** so its default actually takes effect:

- Ensure `seed_dev.py` inserts an `AppSettings` row `overlay_pauses_billing = true`. Confirm the other two Phase‑6.5 flags (`require_print_before_release`, `enable_assigned_time_limit`) are already seeded (they were introduced in 6.5.1/6.5.4‑adjacent work) and leave them as‑is.

### 5.4 Agent — close the HUD timer gap (`agent/src/main/ws/client.ts`)

The channel exists (`platform.updateTimer()` → `windows.ts` → `webContents.send('overlay:timer', ...)` → `preload.ts` → `hud.ts` `onTimerUpdate`) but is never driven. Fix: in `startElapsedTimer()`'s existing 10s `setInterval` callback (currently only calls `store.updateElapsed`), also push the timer:

```ts
this.persistTimer = setInterval(() => {
  if (this.sessionState.session_id && this.sessionState.started_at) {
    const startedAtMs = new Date(this.sessionState.started_at).getTime();
    const elapsed = Math.floor((Date.now() - startedAtMs) / 1000);
    this.store?.updateElapsed(this.sessionState.session_id, elapsed);
    this.updateTimer({ elapsedSeconds: elapsed });   // NEW — drives the HUD countdown
  }
}, 10_000);
```

- **Structured payload, not a pre‑formatted string.** `updateTimer()` currently emits `{ timeString }`; change the IPC contract to carry `{ elapsedSeconds: number }` so Epic 6.5.4 can later extend the same channel to `{ elapsedSeconds, assignedEndAt, remainingSeconds }` without re‑touching this fan‑out. Update `windows.ts updateTimer()`, `preload.ts onTimerUpdate`, and `renderer/hud.ts` to format `elapsedSeconds` (e.g. `HH:MM:SS` counting up from session start).
- **No server involvement.** The agent already owns `started_at` and ticks locally; this survives LAN drops. The 10s cadence is unchanged — we only add a sibling call.
- The agent's session timer (`startElapsedTimer`) keeps running through a forced overlay, so the countdown survives force‑on/off as well.

## 6. Key Decisions (resolved during brainstorming)

| # | Decision | Rationale |
|---|-----------|-----------|
| 1 | Forced overlay on an **ACTIVE** session = real **PAUSED** transition (unified pause path) | Checkpoint 6.5‑A requires "same accrual path as `pause_session()` — no drift". One source of truth. |
| 2 | HUD countdown driven **agent‑locally** from the existing 10s cadence | Matches Epic 6.5.3 task wording; survives LAN drops; no new server scheduler loop. Supersedes the Epic 5.5 "server push" note. |
| 3 | **Always resume on force‑off** (no `paused_by_overlay` column) | Simpler; avoids a migration. Accepted trade‑off: forcing the overlay off on a *manually*‑paused session will resume billing (see §7). |

Forced overlay uses `FORCE_OVERLAY_ON/OFF` (not `SHOW_OVERLAY`/`HIDE_OVERLAY`) deliberately: `FORCE_OVERLAY_*` is independent of the `STAFF_OVERRIDE` suppression logic, whereas `SHOW_OVERLAY` is suppressed while an override is active. A forced overlay must show even during an override.

## 7. Known Limitations

- **Force‑off resumes manually‑paused sessions.** Because we deliberately skipped a `paused_by_overlay` column (Decision 3), `force_overlay(show=False)` resumes *any* PAUSED session on the seat. If a session was manually paused and the admin then force‑overlays and force‑un‑overlays that seat, billing resumes even though the staff intended a manual pause. Acceptable for v1.0; revisit if venues report surprising resumes.
- **Agent‑local elapsed ignores server‑side pauses.** The agent's `elapsed` is wall‑clock since `started_at`; it does not subtract `total_paused_seconds`. For v1.0 (no `assigned_end_at`) a counting‑up session timer is fine. Epic 6.5.4 will introduce authoritative remaining‑time via the server (`assignedEndAt`/`remainingSeconds` in the same `overlay:timer` payload), at which point the agent should prefer the server value when present.

## 8. Error Handling

- `force_overlay` continues to raise `404` for an unknown seat and `503` when the agent is offline (existing behaviour); the session‑state changes happen *after* the agent send succeeds, so an offline agent still performs no DB mutation (unchanged contract).
- If `get_active_by_seat` returns `None` (no session on the seat), both branches behave as pure lock control (set flag, send command, audit) — identical to today.
- The `FORCE_OVERLAY_ON` payload enrichment (`session_id`/`started_at`) is best‑effort: the agent's `FORCE_OVERLAY_ON` handler already does `sessionActive: !!payload.session_id`, so an empty payload just yields `sessionActive: false` (current behaviour) without error.

## 9. Testing

**Backend — `backend/tests/test_remote_commands.py`** (extend existing `force_overlay` tests, which currently mock `set_overlay_forced`):
- `force_overlay(show=True)` on a seat with an ACTIVE session + flag `true` → session `status == PAUSED`, `seat.status == PAUSED`, `total_paused_seconds` unchanged yet, `FORCE_OVERLAY_ON` payload carries `session_id`.
- `force_overlay(show=False)` on that seat → session `status == ACTIVE`, `total_paused_seconds` increased by the pause duration, `seat.status == IN_USE`.
- Flag `false` → `force_overlay` leaves session/status untouched (pure lock), still sets `overlay_forced` and audits.
- `force_overlay(show=True)` on an idle seat (no session) → pure lock, no `get_active_by_seat` mutation.

**Backend — `backend/tests/test_session_service.py`** (parity, satisfies Checkpoint 6.5‑A):
- Drive an ACTIVE session through `pause_session`+`resume_session` and, in a separate case, through `force_overlay(True)`+`force_overlay(False)`; assert the resulting `total_paused_seconds` is **identical** for the same wall‑clock duration (no drift between the two paths).

**Agent — `agent` vitest** (per TODO Testing Requirements):
- `startElapsedTimer` callback emits `overlay:timer` with `{ elapsedSeconds }` every 10s.
- `FORCE_OVERLAY_ON`/`FORCE_OVERLAY_OFF` handlers do **not** collide with the `STAFF_OVERRIDE` suppression logic (overlay still shows/hides during an override).

**Frontend:** no change required (the HUD countdown is agent‑rendered). `SeatCard` already renders `overlay_forced` and `PAUSED`.

## 10. Documentation

- `docs/TODO.md`: tick the two Epic 6.5.3 task boxes; tick the Checkpoint 6.5‑A item *"Forcing overlay on … pauses billed time using the same accrual path as `pause_session()` — no drift between the two"*. Appendix D already lists `overlay_pauses_billing` (default `true`) — no change needed.
- `docs/operator-guide.md`: add a note distinguishing **Force Overlay** (owner lock; can pause billing when `overlay_pauses_billing=true`) from **Pause** (staff session hold). (Operator guide is a Phase‑6.5 documentation deliverable; add the note here or in the Phase‑6.5 doc pass.)
- No API‑reference change (no new endpoints; `FORCE_OVERLAY_ON` payload growth is internal to the WS contract, already covered by Appendix A).

## 11. Implementation Order (suggested, for the writing‑plans step)

1. §5.3 seed the flag (unblocks correct default behaviour).
2. §5.1 extract `_begin_pause`/`_accrue_pause`; refactor `pause_session`/`resume_session`; add parity test.
3. §5.2 extend `force_overlay` (flag gate + session state + payload enrichment); extend `test_remote_commands`.
4. §5.4 agent `overlay:timer` fan‑out + structured payload + IPC contract update; agent vitest.
5. §10 docs.

## 12. Open Questions

- None outstanding. All three brainstorming forks (unified pause / agent‑local tick / always‑resume) are resolved and reflected in §6.
