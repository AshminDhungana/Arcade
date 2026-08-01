# Seat Online/Offline Status — Design Spec

**Date:** 2026-08-01
**Status:** Approved
**Author:** Ashmin

---

## Problem Statement

Currently, all seats default to `AVAILABLE` in the database. On server startup, only seats with active sessions get their status corrected (via `recover_active_sessions()`). Seats without active sessions remain `AVAILABLE` even when no agent is connected. This causes the dashboard to incorrectly show "Available" for PCs that are actually offline.

Additionally, when an agent disconnects (heartbeat timeout or explicit disconnect), the seat status is not updated in the database — it retains whatever status it had before.

---

## Solution Overview

Make the database the single source of truth for seat connectivity status:

1. **Startup**: Mark all seats without active sessions as `OFFLINE`
2. **Agent REGISTER**: Update seat status in DB to `AVAILABLE` (or `IN_USE`/`PAUSED` if session exists)
3. **Agent disconnect**: Update seat status in DB to `OFFLINE` (if no active session)
4. **WoL flow**: Unchanged (`BOOTING` → `AVAILABLE` on success, `UNREACHABLE` on timeout)

---

## Detailed Design

### 1. Startup Initialization

**File:** `backend/core/startup.py`

Add new function `initialize_seat_statuses()`:

```python
async def initialize_seat_statuses() -> None:
    """Mark all seats without active sessions as OFFLINE on startup."""
    from backend.core.database import AsyncSessionLocal
    from backend.models._enums import SeatStatus, SessionStatus
    from backend.repositories import seat_repo, session_repo

    async with AsyncSessionLocal() as db:
        # Get all seat IDs that have an active session
        active_sessions = await session_repo.list_active(db)
        active_seat_ids = {s.seat_id for s in active_sessions}

        # Get all seats
        all_seats = await seat_repo.list_all(db)

        # Set seats without active sessions to OFFLINE
        for seat in all_seats:
            if seat.id not in active_seat_ids:
                if seat.status != SeatStatus.OFFLINE:
                    seat.status = SeatStatus.OFFLINE
                    await seat_repo.update(db, seat)
```

**File:** `backend/main.py` (lifespan)

Add call to `initialize_seat_statuses()` after `recover_active_sessions()` and before `boot_all_seats()`:

```python
async def lifespan(app: FastAPI):
    await run_migrations()
    await recover_active_sessions()
    await initialize_seat_statuses()  # NEW
    await boot_all_seats()
    ...
```

### 2. Agent REGISTER Handler

**File:** `backend/core/ws_manager.py` — `_handle_register()`

After broadcasting "ONLINE" to dashboards, update seat status in database:

```python
async def _handle_register(self, seat_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    # ... existing broadcast code ...

    # NEW: Update seat status in DB based on session state
    from backend.core.database import AsyncSessionLocal
    from backend.models._enums import SeatStatus, SessionStatus
    from backend.repositories import seat_repo, session_repo

    async with AsyncSessionLocal() as db:
        seat = await seat_repo.get_by_id(db, seat_id)
        if seat is not None:
            # Check for active session
            active_session = await session_repo.get_active_by_seat(db, seat_id)
            if active_session is not None:
                new_status = (
                    SeatStatus.PAUSED
                    if active_session.status == SessionStatus.PAUSED
                    else SeatStatus.IN_USE
                )
            else:
                new_status = SeatStatus.AVAILABLE

            if seat.status != new_status:
                seat.status = new_status
                await seat_repo.update(db, seat)

            # Broadcast updated status to dashboards
            await self.broadcast_to_dashboards(
                Msg.SEAT_UPDATED,
                {"seat_id": seat_id, "status": seat.status.value},
            )

    # ... existing WoL callback and return ...
```

**Note:** This replaces the `wol_success_callback` call for non-`BOOTING` seats. The `wol_success_callback` remains for the specific `BOOTING` → `AVAILABLE` transition during WoL.

### 3. Agent Disconnect Handler

**File:** `backend/core/ws_manager.py` — `disconnect_agent()`

```python
async def disconnect_agent(self, seat_id: str) -> None:
    # ... existing cleanup code (screenshot futures, pending_pongs, agent_connections) ...

    # NEW: Update seat status in DB to OFFLINE (if no active session)
    from backend.core.database import AsyncSessionLocal
    from backend.models._enums import SeatStatus, SessionStatus
    from backend.repositories import seat_repo, session_repo

    async with AsyncSessionLocal() as db:
        seat = await seat_repo.get_by_id(db, seat_id)
        if seat is not None:
            # Only set to OFFLINE if no active session
            active_session = await session_repo.get_active_by_seat(db, seat_id)
            if active_session is None and seat.status != SeatStatus.OFFLINE:
                seat.status = SeatStatus.OFFLINE
                await seat_repo.update(db, seat)

                # Broadcast to dashboards
                await self.broadcast_to_dashboards(
                    Msg.SEAT_UPDATED,
                    {"seat_id": seat_id, "status": SeatStatus.OFFLINE.value},
                )
```

**Heartbeat timeout in `_tick()`** — already removes agent from `agent_connections` and closes WebSocket. The `disconnect_agent()` call is not automatic there, so we need to ensure the DB update happens. Option: refactor `_tick()` to call `disconnect_agent()` for expired agents, or duplicate the DB update logic. **Decision:** Call `disconnect_agent()` from `_tick()` for consistency.

```python
async def _tick(self) -> None:
    # Step 1: Disconnect agents who didn't PONG from the PREVIOUS tick
    expired = list(self._pending_pongs)
    for seat_id in expired:
        # NEW: Use disconnect_agent for proper cleanup + DB update
        await self.disconnect_agent(seat_id)

    # Step 2: Send PING to all current agents
    ...
```

### 4. WoL Flow Compatibility

The WoL flow remains unchanged:

1. `boot_all_seats()` → sends magic packets, sets seats to `BOOTING`, starts 60s watchdog
2. Watchdog timeout → sets seat to `UNREACHABLE` (if still `BOOTING`)
3. Agent REGISTER during `BOOTING` → `wol_success_callback()` sets seat to `AVAILABLE`

**With new design:**
- Startup: All seats without active sessions → `OFFLINE`
- `boot_all_seats()` transitions MAC seats: `OFFLINE` → `BOOTING`
- Watchdog: `BOOTING` → `UNREACHABLE` (unchanged)
- Agent REGISTER: `BOOTING`/`OFFLINE`/`UNREACHABLE` → `AVAILABLE` (or `IN_USE`/`PAUSED`)

**Edge case:** If agent registers while seat is `UNREACHABLE` (after WoL timeout), the new `_handle_register` logic correctly transitions to `AVAILABLE`/`IN_USE`.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        SERVER STARTUP                           │
├─────────────────────────────────────────────────────────────────┤
│  1. recover_active_sessions()                                   │
│     - Seats with ACTIVE/PAUSED sessions → IN_USE/PAUSED        │
│  2. initialize_seat_statuses()                                  │
│     - All other seats → OFFLINE                                 │
│  3. boot_all_seats()                                            │
│     - MAC seats: OFFLINE → BOOTING (watchdog starts)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT CONNECTS                             │
├─────────────────────────────────────────────────────────────────┤
│  Agent sends REGISTER                                           │
│  _handle_register():                                            │
│    - Check for active session                                   │
│    - If active: IN_USE (or PAUSED)                              │
│    - If none: AVAILABLE                                         │
│    - Update DB + broadcast                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT DISCONNECTS                          │
├─────────────────────────────────────────────────────────────────┤
│  disconnect_agent() (explicit or heartbeat timeout):            │
│    - If no active session: seat → OFFLINE                       │
│    - Update DB + broadcast                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Changes Needed

Add new method to `session_repo.py`:

```python
async def get_active_by_seat(db: AsyncSession, seat_id: str) -> Session | None:
    """Get active (ACTIVE or PAUSED) session for a seat."""
    result = await db.execute(
        select(Session).where(
            Session.seat_id == seat_id,
            Session.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED])
        )
    )
    return result.scalar_one_or_none()
```

---

## Testing Strategy

### Unit Tests (new/modified)

1. `test_startup_initializes_seats_offline()` — verify seats without active sessions start as `OFFLINE`
2. `test_agent_register_updates_seat_status()` — verify REGISTER sets correct status based on session state
3. `test_agent_disconnect_sets_offline()` — verify disconnect sets seat to `OFFLINE` (if no active session)
4. `test_wol_flow_still_works()` — verify WoL: `OFFLINE` → `BOOTING` → `AVAILABLE`/`UNREACHABLE`
5. `test_register_after_wol_timeout()` — verify REGISTER works from `UNREACHABLE` state

### Integration Tests

- Full startup → agent connect → agent disconnect cycle
- WoL + agent register race conditions

### Existing Tests to Update

- Any tests that assume seats default to `AVAILABLE` on startup

---

## Rollback Plan

If issues arise:
1. Revert `initialize_seat_statuses()` call in lifespan
2. Revert `_handle_register()` DB update logic
3. Revert `disconnect_agent()` DB update logic
4. Seats will return to defaulting to `AVAILABLE` (current behavior)

---

## Open Questions

None — all design decisions confirmed during review.

---

## Implementation Checklist

- [ ] Add `initialize_seat_statuses()` to `backend/core/startup.py`
- [ ] Call it in `backend/main.py` lifespan
- [ ] Add `get_active_by_seat()` to `backend/repositories/session_repo.py`
- [ ] Update `_handle_register()` in `backend/core/ws_manager.py`
- [ ] Update `disconnect_agent()` in `backend/core/ws_manager.py`
- [ ] Update `_tick()` to call `disconnect_agent()` for expired agents
- [ ] Write unit tests
- [ ] Run integration tests
- [ ] Verify dashboard shows correct status throughout lifecycle