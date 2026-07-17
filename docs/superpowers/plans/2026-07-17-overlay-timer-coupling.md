# Epic 6.5.3: Overlay ↔ Timer Coupling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify forced overlay with the existing pause-accounting path (so forcing the overlay on an active session pauses billing via the same helper as `pause_session`) and make the in-game HUD countdown tick by driving the agent's already-present `overlay:timer` channel from its 10s session cadence.

**Architecture:** Backend extracts two pure pause-accounting helpers (`_begin_pause`/`_accrue_pause`) in `session_service` and reuses them from `remote_command_service.force_overlay` behind the `overlay_pauses_billing` flag. Agent adds a one-line fan-out in its existing 10s timer to call `platform.updateTimer()` with a structured `{ elapsedSeconds }` payload (the channel already exists but was never driven).

**Tech Stack:** Python 3 / FastAPI / async SQLAlchemy (backend); TypeScript / Electron (agent); pytest (backend tests); vitest (agent tests).

## Global Constraints

- `overlay_pauses_billing` default is `true` (Appendix D) — but `core/feature_flags.get_flag()` returns `False` for any unknown key, so it **must be seeded** (`seed_dev.py`).
- Forced overlay on an **ACTIVE** session = real **PAUSED** transition using the same accrual helpers as `pause_session()` — exactly one source of truth (Checkpoint 6.5-A).
- **Always resume on force-off** — no `paused_by_overlay` column. (Known limitation: force-off also resumes a *manually* paused session — accepted footgun, see spec §7.)
- HUD countdown is driven **agent-locally** from the existing 10s `updateElapsed` cadence (no server push).
- `overlay:timer` IPC carries a **structured `{ elapsedSeconds: number }`**, not a pre-formatted string, so Epic 6.5.4 can extend it to `{ elapsedSeconds, assignedEndAt, remainingSeconds }` without re-touching this fan-out.
- Forced overlay uses `FORCE_OVERLAY_ON`/`FORCE_OVERLAY_OFF` (NOT `SHOW_OVERLAY`/`HIDE_OVERLAY`) because `FORCE_OVERLAY_*` is independent of the `STAFF_OVERRIDE` suppression logic.
- Money is stored as **integers in paise**; `total_paused_seconds` is an integer. No money math in this epic.

---

## File Structure

**Backend (ENG-A):**
- `backend/scripts/seed_dev.py` — add `overlay_pauses_billing` + `enable_assigned_time_limit` to `DEFAULT_FEATURE_FLAGS`.
- `backend/services/session_service.py` — add module-level `_begin_pause()` / `_accrue_pause()`; refactor `pause_session()` / `resume_session()` to call them.
- `backend/services/remote_command_service.py` — import `session_repo`, `session_service`, `feature_flags`; add `_broadcast_seat_updated()`; rewrite `force_overlay()` to manage session state behind the flag and enrich the `FORCE_OVERLAY_ON` payload.
- `backend/tests/test_session_service.py` — add accrual-parity test (Checkpoint 6.5-A).
- `backend/tests/test_remote_commands.py` — add `active_session` fixture + force-overlay pause/resume/flag tests.

**Agent (ENG-B):**
- `agent/src/main/platform/types.ts` — `updateTimer(timer: { elapsedSeconds: number }): void`.
- `agent/src/main/platform/windows.ts` — `updateTimer` impl emits `{ elapsedSeconds }`.
- `agent/src/main/ws/client.ts` — `startElapsedTimer` 10s callback calls `this.platform.updateTimer({ elapsedSeconds })`.
- `agent/src/renderer/preload.ts` — `onTimerUpdate` contract becomes `{ elapsedSeconds }`.
- `agent/src/renderer/index.ts` — `onTimerUpdate` type + format elapsed for the kiosk overlay.
- `agent/src/renderer/hud.ts` — `onTimerUpdate` formats elapsed for the in-game HUD.
- `agent/tests/platform.test.ts` — update `updateTimer` call + assertions to the new payload.

**Docs:**
- `docs/TODO.md` — tick Epic 6.5.3 + Checkpoint 6.5-A boxes.
- `docs/operator-guide.md` — note distinguishing Force Overlay from Pause (Phase 6.5 doc deliverable).

---

### Task 1: Seed the `overlay_pauses_billing` feature flag

**Files:**
- Modify: `backend/scripts/seed_dev.py:207-221` (`DEFAULT_FEATURE_FLAGS`)

**Interfaces:**
- Consumes: nothing.
- Produces: `AppSettings` rows for `overlay_pauses_billing=true` and `enable_assigned_time_limit=false` at seed time (required so `get_flag` returns the documented defaults).

- [ ] **Step 1: Add the two missing flags to `DEFAULT_FEATURE_FLAGS`**

In `backend/scripts/seed_dev.py`, replace the tail of the `DEFAULT_FEATURE_FLAGS` dict:

```python
DEFAULT_FEATURE_FLAGS: dict[str, str] = {
    "enable_members": "true",
    "enable_packages": "true",
    "enable_pos": "true",
    "enable_inventory": "false",
    "enable_reservations": "true",
    "enable_vouchers": "false",
    "enable_tournaments": "false",
    "enable_expense_tracking": "false",
    "enable_health_monitoring": "true",
    "require_member_for_session": "false",
    "enable_tuya": "false",
    "require_print_before_release": "false",
    "block_shift_close_unprinted": "false",
    "overlay_pauses_billing": "true",        # NEW (Phase 6.5.3)
    "enable_assigned_time_limit": "false",   # NEW (Phase 6.5.4; seed now so Appendix D defaults hold)
}
```

- [ ] **Step 2: Compile-check the script**

Run: `cd "E:/Ongoing Projects/Arcade/backend" && python -m py_compile scripts/seed_dev.py`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/seed_dev.py
git commit -m "feat(6.5.3): seed overlay_pauses_billing flag (default true)"
```

---

### Task 2: Extract pause-accounting helpers in `session_service`

**Files:**
- Modify: `backend/services/session_service.py:70-92` (after `_session_to_response`) — add helpers
- Modify: `backend/services/session_service.py:256-259` (`pause_session` update block)
- Modify: `backend/services/session_service.py:322-329` (`resume_session` accrual block)

**Interfaces:**
- Consumes: `SessionStatus`, `_ensure_tz` (both already in module).
- Produces: `session_service._begin_pause(session, now)` and `session_service._accrue_pause(session, now)` — used by `pause_session`, `resume_session`, and (Task 3) `force_overlay`.

- [ ] **Step 1: Add the two helper functions** (insert after `_session_to_response`, before `# Public API`)

```python
def _begin_pause(session: GamingSession, now: datetime) -> None:
    """Record pause start. No-op unless the session is ACTIVE.

    Guards against double-pause: a session already PAUSED keeps its original
    ``paused_at`` (e.g. a forced overlay on a manually-paused seat).
    """
    if session.status != SessionStatus.ACTIVE:
        return
    session.status = SessionStatus.PAUSED
    session.paused_at = now


def _accrue_pause(session: GamingSession, now: datetime) -> None:
    """Add (now - paused_at) to total_paused_seconds; clear paused_at.

    No-op if ``paused_at`` is already ``None`` (nothing to accrue).
    """
    paused_at = _ensure_tz(session.paused_at)
    if paused_at is None:
        return
    duration = (now - paused_at).total_seconds()
    session.total_paused_seconds = (session.total_paused_seconds or 0) + int(duration)
    session.paused_at = None
```

- [ ] **Step 2: Refactor `pause_session` to call `_begin_pause`**

Replace:

```python
    # Update session
    session.status = SessionStatus.PAUSED
    session.paused_at = datetime.now(UTC)
    session = await session_repo.update(db, session)
```

with:

```python
    # Update session
    _begin_pause(session, datetime.now(UTC))
    session = await session_repo.update(db, session)
```

- [ ] **Step 3: Refactor `resume_session` to call `_accrue_pause`**

Replace:

```python
    # Accumulate pause duration
    paused_at = _ensure_tz(session.paused_at)
    if paused_at:
        pause_duration = (datetime.now(UTC) - paused_at).total_seconds()
        session.total_paused_seconds = (session.total_paused_seconds or 0) + int(
            pause_duration
        )
        session.paused_at = None

    session.status = SessionStatus.ACTIVE
```

with:

```python
    # Accumulate pause duration (single source of truth)
    _accrue_pause(session, datetime.now(UTC))

    session.status = SessionStatus.ACTIVE
```

- [ ] **Step 4: Run existing session tests to confirm the refactor is behaviour-preserving**

Run: `cd "E:/Ongoing Projects/Arcade" && pytest backend/tests/test_session_service.py -v -k "pause or resume"`
Expected: all PASS (no behaviour change — same math, just relocated).

- [ ] **Step 5: Commit**

```bash
git add backend/services/session_service.py
git commit -m "refactor(6.5.3): extract _begin_pause/_accrue_pause helpers"
```

---

### Task 3: Route `force_overlay` through the pause path

**Files:**
- Modify: `backend/services/remote_command_service.py:24-30` (imports)
- Modify: `backend/services/remote_command_service.py:286-319` (`force_overlay`) + add `_broadcast_seat_updated` helper
- Test: `backend/tests/test_remote_commands.py`

**Interfaces:**
- Consumes: `session_service._begin_pause` / `session_service._accrue_pause` (Task 2); `session_repo.get_active_by_seat`; `feature_flags.get_flag`; `SeatStatus` (already imported), `SessionStatus` (add import).
- Produces: `force_overlay(db, seat_id, show, staff)` now also (behind `overlay_pauses_billing`) transitions an ACTIVE session to PAUSED (and back) and enriches the `FORCE_OVERLAY_ON` payload with `{ session_id, started_at }`.

- [ ] **Step 1: Write the failing tests**

Add these to `backend/tests/test_remote_commands.py` (after the existing `force_overlay` tests, ~line 411). First add imports at the top of the file alongside the existing `from backend.repositories import seat_repo`:

```python
from backend.repositories import seat_repo, session_repo
from backend.models import GamingSession
from backend.models._enums import SessionStatus
from datetime import UTC, datetime
```

Then add the fixture (near `staff_member`):

```python
@pytest.fixture
async def active_session(db: AsyncSession, zone_and_seat):
    """Create and return an ACTIVE gaming session on the seat."""
    _, seat = zone_and_seat
    sess = await session_repo.create(
        db, seat_id=seat.id, started_at=datetime.now(UTC), locked_rate_paise=50
    )
    sess.status = SessionStatus.ACTIVE
    await session_repo.update(db, sess)
    return sess
```

Then the tests:

```python
async def test_force_overlay_on_pauses_active_session(
    db: AsyncSession, active_session, staff_member
) -> None:
    """force_overlay(show=True) + flag on -> session PAUSED, seat PAUSED, payload has session_id."""
    from backend.core import feature_flags
    from backend.core.ws_manager import Msg
    from backend.services import remote_command_service as rcs

    sess = active_session
    with (
        patch.object(feature_flags, "get_flag", return_value=True),
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()) as mock_send,
        patch.object(rcs.seat_service, "set_overlay_forced", new=AsyncMock()),
        patch.object(rcs.audit_service, "log", new=AsyncMock()),
        patch.object(rcs.ws_manager, "broadcast_to_dashboards", new=AsyncMock()),
    ):
        await rcs.force_overlay(db, sess.seat_id, True, staff_member)
    refreshed = await session_repo.get_by_id(db, sess.id)
    assert refreshed.status == SessionStatus.PAUSED
    assert refreshed.paused_at is not None
    assert mock_send.call_args.args[1]["type"] == Msg.FORCE_OVERLAY_ON
    assert mock_send.call_args.args[1]["payload"]["session_id"] == sess.id


async def test_force_overlay_off_resumes_and_accrues(
    db: AsyncSession, active_session, staff_member
) -> None:
    """force_overlay(show=False) + flag on -> session ACTIVE again, paused seconds accrued, seat IN_USE."""
    from backend.core import feature_flags
    from backend.core.ws_manager import Msg
    from backend.services import remote_command_service as rcs

    sess = active_session
    with (
        patch.object(feature_flags, "get_flag", return_value=True),
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(rcs.seat_service, "set_overlay_forced", new=AsyncMock()),
        patch.object(rcs.audit_service, "log", new=AsyncMock()),
        patch.object(rcs.ws_manager, "broadcast_to_dashboards", new=AsyncMock()),
    ):
        await rcs.force_overlay(db, sess.seat_id, True, staff_member)
        await rcs.force_overlay(db, sess.seat_id, False, staff_member)
    refreshed = await session_repo.get_by_id(db, sess.id)
    assert refreshed.status == SessionStatus.ACTIVE
    assert refreshed.paused_at is None
    assert refreshed.total_paused_seconds is not None
    assert refreshed.total_paused_seconds >= 0


async def test_force_overlay_ignores_session_when_flag_off(
    db: AsyncSession, active_session, staff_member
) -> None:
    """flag off -> force_overlay never touches the session (pure lock)."""
    from backend.core import feature_flags
    from backend.services import remote_command_service as rcs

    sess = active_session
    with (
        patch.object(feature_flags, "get_flag", return_value=False),
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(rcs.seat_service, "set_overlay_forced", new=AsyncMock()),
        patch.object(rcs.audit_service, "log", new=AsyncMock()),
    ):
        await rcs.force_overlay(db, sess.seat_id, True, staff_member)
    refreshed = await session_repo.get_by_id(db, sess.id)
    assert refreshed.status == SessionStatus.ACTIVE
    assert refreshed.paused_at is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "E:/Ongoing Projects/Arcade" && pytest backend/tests/test_remote_commands.py -v -k "force_overlay_on_pauses or force_overlay_off_resumes or force_overlay_ignores_session"`
Expected: FAIL (session status unchanged / payload missing `session_id` — `force_overlay` doesn't manage sessions yet).

- [ ] **Step 3: Add imports + `_broadcast_seat_updated` helper to `remote_command_service.py`**

Update the import block (lines 24-30):

```python
from backend.core.ws_manager import AgentOfflineError, Msg
from backend.core.ws_manager import manager as ws_manager
from backend.core import feature_flags
from backend.models._enums import AuditAction, SeatStatus, SessionStatus
from backend.models.seat import Seat
from backend.models.staff import Staff
from backend.repositories import seat_repo, session_repo
from backend.services import audit_service, seat_service, session_service
import logging

logger = logging.getLogger(__name__)
```

Add this helper near the top of the file (after the error classes, before `# Helpers` or within it):

```python
async def _broadcast_seat_updated(seat: Seat, session_id: str | None) -> None:
    """Broadcast a seat status change to all dashboards (best-effort)."""
    try:
        await ws_manager.broadcast_to_dashboards(
            "seat_updated",
            {
                "id": seat.id,
                "name": seat.name,
                "status": seat.status.value,
                "current_session_id": session_id,
            },
        )
    except Exception:
        logger.warning(
            "Failed to broadcast seat_updated for %s", seat.id, exc_info=True
        )
```

- [ ] **Step 4: Rewrite `force_overlay`**

Replace the entire function (lines 286-319) with:

```python
async def force_overlay(
    db: AsyncSession,
    seat_id: str,
    show: bool,
    staff: Staff | None = None,
) -> None:
    """Send ``FORCE_OVERLAY_ON``/``OFF`` to the agent, flip ``overlay_forced``, and
    — when ``overlay_pauses_billing`` is enabled and a session is on the seat —
    route the overlay through the pause-accounting path.

    The agent send happens first: if the agent is offline (503) no DB column is
    mutated. Session/seat state changes are applied only after the send succeeds.

    Raises:
        HTTPException(404): If the seat does not exist.
        HTTPException(503): If the agent is offline.
    """
    seat = await _get_seat_or_404(db, seat_id)

    # Read-only: find any in-progress session on this seat.
    session = await session_repo.get_active_by_seat(db, seat_id)
    pauses_billing = feature_flags.get_flag("overlay_pauses_billing")

    begin_pause = (
        show
        and pauses_billing
        and session is not None
        and session.status == SessionStatus.ACTIVE
    )
    resume_pause = (
        (not show)
        and pauses_billing
        and session is not None
        and session.status == SessionStatus.PAUSED
    )

    # Send first so an offline agent aborts before any DB mutation.
    await _send_to_agent_or_503(
        seat_id,
        {
            "type": Msg.FORCE_OVERLAY_ON if show else Msg.FORCE_OVERLAY_OFF,
            "payload": (
                {
                    "session_id": session.id,
                    "started_at": session.started_at.isoformat(),
                }
                if session is not None
                else {}
            ),
        },
    )

    now = datetime.now(UTC)

    if begin_pause and session is not None:
        session_service._begin_pause(session, now)
        await session_repo.update(db, session)
        seat.status = SeatStatus.PAUSED
        await seat_repo.update(db, seat)
        await _broadcast_seat_updated(seat, session.id)

    if resume_pause and session is not None:
        session_service._accrue_pause(session, now)
        session.status = SessionStatus.ACTIVE
        await session_repo.update(db, session)
        seat.status = SeatStatus.IN_USE
        await seat_repo.update(db, seat)
        await _broadcast_seat_updated(seat, session.id)

    await seat_service.set_overlay_forced(db, seat_id, show)
    await audit_service.log(
        db,
        action=(
            AuditAction.OVERLAY_FORCED_ON if show else AuditAction.OVERLAY_FORCED_OFF
        ),
        entity_type="seat",
        entity_id=seat.id,
        staff_id=staff.id if staff else None,
        detail=f"overlay forced={'on' if show else 'off'}",
    )
```

Note: `datetime` must be imported — add `from datetime import UTC, datetime` to the module imports (alongside the other `from __future__` / stdlib imports at the top).

- [ ] **Step 5: Run the new tests + the existing `force_overlay` tests**

Run: `cd "E:/Ongoing Projects/Arcade" && pytest backend/tests/test_remote_commands.py -v -k "force_overlay"`
Expected: all PASS (new + the 4 pre-existing `force_overlay` tests, which are unaffected because they use seats with no session).

- [ ] **Step 6: Commit**

```bash
git add backend/services/remote_command_service.py backend/tests/test_remote_commands.py
git commit -m "feat(6.5.3): route force_overlay through pause accounting"
```

---

### Task 4: Accrual-parity test (Checkpoint 6.5-A)

**Files:**
- Test: `backend/tests/test_session_service.py`

**Interfaces:**
- Consumes: `pause_session`, `resume_session` (public), `remote_command_service.force_overlay` + its helpers (Task 2/3), `session_repo`.
- Produces: a regression guard proving the two flows produce identical `total_paused_seconds`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_session_service.py` (after the existing pause/resume tests). It needs the same `active_session` shape; reuse the file's own `zone_and_seat` + `staff_member` fixtures and create a session inline:

```python
async def test_forced_overlay_accrual_parity_with_pause_resume(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """force_overlay(on/off) must accrue the same total_paused_seconds as pause/resume."""
    from unittest.mock import AsyncMock, patch

    from backend.repositories import session_repo
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat

    # Path A: pause_session -> resume_session
    sess_a = await session_repo.create(
        db, seat_id=seat.id, started_at=datetime.now(UTC), locked_rate_paise=50
    )
    sess_a.status = SessionStatus.ACTIVE
    await session_repo.update(db, sess_a)
    await pause_session(db, sess_a.id, staff_member)
    await resume_session(db, sess_a.id, staff_member)
    path_a = (await session_repo.get_by_id(db, sess_a.id)).total_paused_seconds

    # Path B: force_overlay(True) -> force_overlay(False), flag on
    sess_b = await session_repo.create(
        db, seat_id=seat.id, started_at=datetime.now(UTC), locked_rate_paise=50
    )
    sess_b.status = SessionStatus.ACTIVE
    await session_repo.update(db, sess_b)
    with (
        patch.object(rcs.feature_flags, "get_flag", return_value=True),
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(rcs.seat_service, "set_overlay_forced", new=AsyncMock()),
        patch.object(rcs.audit_service, "log", new=AsyncMock()),
        patch.object(rcs.ws_manager, "broadcast_to_dashboards", new=AsyncMock()),
    ):
        await rcs.force_overlay(db, seat.id, True, staff_member)
        await rcs.force_overlay(db, seat.id, False, staff_member)
    path_b = (await session_repo.get_by_id(db, sess_b.id)).total_paused_seconds

    assert isinstance(path_a, int) and isinstance(path_b, int)
    assert path_a == path_b
```

Ensure `from backend.models._enums import SessionStatus` and `from datetime import UTC, datetime` are imported in this test module (add if absent).

- [ ] **Step 2: Run the test to verify it passes**

Run: `cd "E:/Ongoing Projects/Arcade" && pytest backend/tests/test_session_service.py::test_forced_overlay_accrual_parity_with_pause_resume -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_session_service.py
git commit -m "test(6.5.3): assert forced-overlay accrual parity with pause/resume"
```

---

### Task 5: Agent — `updateTimer` takes a structured payload

**Files:**
- Modify: `agent/src/main/platform/types.ts:100-107` (`updateTimer` interface)
- Modify: `agent/src/main/platform/windows.ts:158-163` (`updateTimer` impl)

**Interfaces:**
- Consumes: nothing new.
- Produces: `IPlatformService.updateTimer(timer: { elapsedSeconds: number })` — contract change consumed by `ws/client.ts` (Task 6) and the renderers (Task 7).

- [ ] **Step 1: Change the interface in `types.ts`**

Replace:

```ts
  /**
   * Update the visible timer display on the active overlay (HUD during a
   * session, kiosk when idle).
   *
   * Must be called after `showKioskOverlay`/`showHud`. No-op if the relevant
   * window is not visible.
   */
  updateTimer(timeString: string): void;
```

with:

```ts
  /**
   * Update the visible timer display on the active overlay (HUD during a
   * session, kiosk when idle) with the elapsed session time in seconds.
   *
   * `elapsedSeconds` is wall-clock seconds since session start (agent-local;
   * survives LAN drops). Epic 6.5.4 will extend this to include
   * `assignedEndAt`/`remainingSeconds` without changing this call site.
   *
   * Must be called after `showKioskOverlay`/`showHud`. No-op if the relevant
   * window is not visible.
   */
  updateTimer(timer: { elapsedSeconds: number }): void;
```

- [ ] **Step 2: Change the implementation in `windows.ts`**

Replace:

```ts
  updateTimer(timeString: string): void {
    const win = this.sessionActive ? this.hudWindow : this.kioskWindow;
    if (win && !win.isDestroyed()) {
      win.webContents.send('overlay:timer', { timeString });
    }
  }
```

with:

```ts
  updateTimer(timer: { elapsedSeconds: number }): void {
    const win = this.sessionActive ? this.hudWindow : this.kioskWindow;
    if (win && !win.isDestroyed()) {
      win.webContents.send('overlay:timer', { elapsedSeconds: timer.elapsedSeconds });
    }
  }
```

- [ ] **Step 3: Type-check the agent**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx tsc --noEmit -p tsconfig.json`
Expected: no errors referencing `updateTimer` (the call sites in `ws/client.ts` and renderers are updated in Tasks 6-7).

- [ ] **Step 4: Commit**

```bash
git add agent/src/main/platform/types.ts agent/src/main/platform/windows.ts
git commit -m "refactor(agent): updateTimer takes structured { elapsedSeconds }"
```

---

### Task 6: Agent — drive `overlay:timer` from the 10s cadence

**Files:**
- Modify: `agent/src/main/ws/client.ts:492-505` (`startElapsedTimer`)

**Interfaces:**
- Consumes: `IPlatformService.updateTimer({ elapsedSeconds })` (Task 5).
- Produces: the HUD countdown now ticks every 10s; same behaviour the renderers consume (Task 7).

- [ ] **Step 1: Add the fan-out in `startElapsedTimer`**

Replace the `startElapsedTimer` body:

```ts
  private startElapsedTimer(): void {
    if (this.persistTimer) {
      clearInterval(this.persistTimer);
      this.persistTimer = null;
    }
    this.persistTimer = setInterval(() => {
      if (this.sessionState.session_id && this.sessionState.started_at) {
        const startedAtMs = new Date(this.sessionState.started_at).getTime();
        const elapsed = Math.floor((Date.now() - startedAtMs) / 1000);
        this.store?.updateElapsed(this.sessionState.session_id, elapsed);
        this.platform.updateTimer({ elapsedSeconds: elapsed });
      }
    }, 10_000);
  }
```

(The only change vs. the current code is the added `this.platform.updateTimer({ elapsedSeconds: elapsed });` line.)

- [ ] **Step 2: Type-check the agent**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx tsc --noEmit -p tsconfig.json`
Expected: PASS (no type errors).

- [ ] **Step 3: Commit**

```bash
git add agent/src/main/ws/client.ts
git commit -m "feat(agent): tick HUD overlay:timer from the 10s session cadence"
```

---

### Task 7: Agent — renderers consume `{ elapsedSeconds }`

**Files:**
- Modify: `agent/src/renderer/preload.ts:28-29,62-64`
- Modify: `agent/src/renderer/index.ts:17,48-50`
- Modify: `agent/src/renderer/hud.ts:44-46`

**Interfaces:**
- Consumes: `overlay:timer` IPC carrying `{ elapsedSeconds: number }` (Tasks 5-6).
- Produces: both the kiosk overlay (`index.ts`) and the in-game HUD (`hud.ts`) render a formatted `HH:MM:SS` elapsed countdown.

- [ ] **Step 1: Update `preload.ts` contract**

Replace the `onTimerUpdate` interface line (29):

```ts
  /** Main → Renderer: update the visible timer string. */
  onTimerUpdate: (callback: (timeString: string) => void) => void;
```

with:

```ts
  /** Main → Renderer: update the visible timer (elapsed seconds since session start). */
  onTimerUpdate: (callback: (timer: { elapsedSeconds: number }) => void) => void;
```

Replace the handler (62-64):

```ts
  onTimerUpdate: (callback) => {
    ipcRenderer.on('overlay:timer', (_event, data) => callback(data.timeString));
  },
```

with:

```ts
  onTimerUpdate: (callback) => {
    ipcRenderer.on('overlay:timer', (_event, data) => callback(data));
  },
```

- [ ] **Step 2: Update `index.ts` (kiosk overlay)**

Replace the `Window.electronAPI` type line (17):

```ts
      onTimerUpdate: (callback: (timeString: string) => void) => void;
```

with:

```ts
      onTimerUpdate: (callback: (timer: { elapsedSeconds: number }) => void) => void;
```

Replace the listener (48-50):

```ts
  window.electronAPI.onTimerUpdate((timeString) => {
    overlay.setTimer(timeString);
  });
```

with:

```ts
  window.electronAPI.onTimerUpdate((timer) => {
    overlay.setTimer(formatElapsed(timer.elapsedSeconds));
  });
```

Add a `formatElapsed` helper near the top of `index.ts` (after the `import` block, before `initKiosk`):

```ts
/** Format elapsed seconds as HH:MM:SS (counts up from session start). */
function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
}
```

- [ ] **Step 3: Update `hud.ts` (in-game HUD)**

Replace (44-46):

```ts
  window.electronAPI.onTimerUpdate((timeString) => {
    timer.textContent = timeString;
  });
```

with:

```ts
  window.electronAPI.onTimerUpdate((timer) => {
    timer.textContent = formatElapsed(timer.elapsedSeconds);
  });
```

Add a `formatElapsed` helper at the top of `hud.ts` (after the `import` line):

```ts
/** Format elapsed seconds as HH:MM:SS (counts up from session start). */
function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
}
```

- [ ] **Step 4: Type-check the agent**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx tsc --noEmit -p tsconfig.json`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/preload.ts agent/src/renderer/index.ts agent/src/renderer/hud.ts
git commit -m "feat(agent): render overlay:timer elapsed countdown in both overlays"
```

---

### Task 8: Agent — update `platform.test.ts` to the new payload

**Files:**
- Modify: `agent/tests/platform.test.ts:37,41-42`

**Interfaces:**
- Consumes: `WindowsPlatformService.updateTimer({ elapsedSeconds })` (Task 5).
- Produces: passing agent test suite.

- [ ] **Step 1: Update the test call + assertions**

Replace (37):

```ts
    svc.updateTimer('00:05:00');
```

with:

```ts
    svc.updateTimer({ elapsedSeconds: 300 });
```

Replace (41-42):

```ts
    expect(hud.sent['overlay:timer']).toBeTruthy();
    expect(kiosk.sent['overlay:timer']).toBeUndefined();
```

with:

```ts
    expect(hud.sent['overlay:timer']).toEqual([{ elapsedSeconds: 300 }]);
    expect(kiosk.sent['overlay:timer']).toBeUndefined();
```

- [ ] **Step 2: Run the agent test**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx vitest run tests/platform.test.ts`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add agent/tests/platform.test.ts
git commit -m "test(agent): update platform timer test to structured payload"
```

---

### Task 9: Docs — tick Epic 6.5.3 + Checkpoint 6.5-A

**Files:**
- Modify: `docs/TODO.md` (Epic 6.5.3 task boxes + Checkpoint 6.5-A item)
- Modify: `docs/operator-guide.md` (Force Overlay vs Pause note)

**Interfaces:**
- Consumes: the implemented behaviour.
- Produces: accurate project tracking.

- [ ] **Step 1: Tick the Epic 6.5.3 boxes in `docs/TODO.md`**

Change the two unchecked boxes under "Epic 6.5.3":

```markdown
- [x] **Task: Route forced overlay through the pause accounting path**
  - [x] **Modifies Feature 2.1.2 (Session Service, `pause_session()`):** ...
  - [x] Make the behaviour config-driven, not hardcoded: new flag `overlay_pauses_billing` (default `true`) ...
- [x] **Task: Close the documented HUD gap** - ...
```

and the Checkpoint 6.5-A item:

```markdown
- [x] Forcing overlay on (manually or via time expiry) pauses billed time using the same accrual path as `pause_session()` - no drift between the two
```

- [ ] **Step 2: Add the operator-guide note**

In `docs/operator-guide.md`, under the Phase 6.5 section (or a new "Overlay & Pause" subsection), add:

```markdown
### Force Overlay vs Pause

- **Pause** (staff action on an active session) holds the seat and stops billed time for that session only.
- **Force Overlay** (owner/dashboard) shows the kiosk lock on any seat regardless of session state and is audit-logged. When the `overlay_pauses_billing` setting is ON (default), forcing the overlay on a seat with an active session also pauses that session's billed time using the exact same accounting as Pause — so there is no drift between the two. Turning `overlay_pauses_billing` OFF makes Force Overlay a pure lock (an "Overtime"-style mode) that never touches billing.

Known limitation: turning the forced overlay OFF resumes any paused session on that seat, including one a staff member paused manually.
```

- [ ] **Step 3: Commit**

```bash
git add docs/TODO.md docs/operator-guide.md
git commit -m "docs(6.5.3): mark epic complete; add Force Overlay vs Pause note"
```

---

## Self-Review Notes (per skill checklist)

- **Spec coverage:** §1 helpers → Task 2; §2 `force_overlay` coupling + flag → Task 3 + Task 1 (seed); §3 agent tick → Tasks 5-8; §9 tests → Tasks 3-4 + 8; §10 docs → Task 9. All spec sections mapped.
- **Placeholder scan:** no TBD/TODO/“implement later”; every code step shows the actual code.
- **Type consistency:** `updateTimer({ elapsedSeconds: number })` is the single contract in Tasks 5→6→7→8; `formatElapsed(seconds: number): string` is identical in `index.ts` and `hud.ts`; `force_overlay(db, seat_id, show, staff)` signature unchanged from spec; `_begin_pause`/`_accrue_pause` names match between Task 2 (definition) and Task 3 (use via `session_service._begin_pause`).
- **Two spec deviations handled:** `seed_dev.py` was missing both `overlay_pauses_billing` and `enable_assigned_time_limit` (Task 1 adds both); the `overlay:timer` consumers are two renderers + one test (all updated in Tasks 7-8), not one.
