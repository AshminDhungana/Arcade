# Seat Online/Offline Status Tracking — Design Spec

**Date:** 2026-08-01
**Status:** Approved
**Author:** Assistant

---

## 1. Overview

Implement automatic seat online/offline status tracking so the dashboard accurately reflects which gaming stations are currently connected to the server via their agents.

- **Startup:** All seats initialized to `OFFLINE`
- **Agent connects (REGISTER):** Seat → `ONLINE`
- **Agent disconnects (clean or heartbeat timeout):** Seat → `OFFLINE`
- **Dashboard updates:** Real-time via WebSocket `SEAT_UPDATED` broadcasts

---

## 2. Architecture

### 2.1 Components

| Component | Responsibility |
|-----------|----------------|
| `startup.initialize_seat_statuses()` | Boot-time: set all seats `OFFLINE`, broadcast |
| `ws_manager._handle_register()` | Agent connects: set seat `ONLINE`, broadcast |
| `ws_manager.disconnect_agent()` | Agent disconnects: set seat `OFFLINE`, broadcast |
| `seat_repo.get_all_seat_ids()` | Helper for startup to fetch all seat IDs |

### 2.2 Data Flow

```
Server Start
    │
    ▼
initialize_seat_statuses()
    ├─► SELECT id FROM seats
    ├─► UPDATE seats SET status='OFFLINE'
    └─► broadcast SEAT_UPDATED (status=OFFLINE) for each seat
    │
    ▼
Agent connects → REGISTER
    │
    ▼
_handle_register(seat_id)
    ├─► UPDATE seats SET status='ONLINE'
    └─► broadcast SEAT_UPDATED (status=ONLINE)
    │
    ▼
Agent disconnects (clean / heartbeat timeout)
    │
    ▼
disconnect_agent(seat_id)
    ├─► UPDATE seats SET status='OFFLINE'
    └─► broadcast SEAT_UPDATED (status=OFFLINE)
```

---

## 3. File Changes

### 3.1 `backend/core/startup.py`

```python
async def initialize_seat_statuses() -> None:
    """Set all seats to OFFLINE on server startup and broadcast to dashboards."""
    from backend.core.database import AsyncSessionLocal
    from backend.repositories import seat_repo
    from backend.models._enums import SeatStatus
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import Seat

    async with AsyncSessionLocal() as db:
        seat_ids = await seat_repo.get_all_seat_ids(db)
        for seat_id in seat_ids:
            await seat_repo.update_status(db, seat_id, SeatStatus.OFFLINE)
            # Broadcast to dashboards
            seat = await db.get(Seat, seat_id)
            if seat:
                await ws_manager.broadcast_to_dashboards("seat_updated", {
                    "seat_id": seat_id,
                    "status": "OFFLINE",
                })
        await db.commit()
```

### 3.2 `backend/main.py` (lifespan)

Add call after `run_migrations()`, before `recover_active_sessions()`:

```python
await run_migrations()
await initialize_seat_statuses()  # NEW
await recover_active_sessions()
await boot_all_seats()
```

### 3.3 `backend/core/ws_manager.py`

**`_handle_register()`** — add status update after successful auth:

```python
async def _handle_register(self, seat_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    # ... existing code ...
    # After broadcasting current REGISTER payload:
    from backend.core.database import AsyncSessionLocal
    from backend.repositories import seat_repo
    from backend.models._enums import SeatStatus

    async with AsyncSessionLocal() as db:
        await seat_repo.update_status(db, seat_id, SeatStatus.ONLINE)
        await db.commit()
    # ... rest unchanged ...
```

**`disconnect_agent()`** — add status update:

```python
async def disconnect_agent(self, seat_id: str) -> None:
    # ... existing cleanup code ...
    # After removing from agent_connections:
    from backend.core.database import AsyncSessionLocal
    from backend.repositories import seat_repo
    from backend.models._enums import SeatStatus

    async with AsyncSessionLocal() as db:
        await seat_repo.update_status(db, seat_id, SeatStatus.OFFLINE)
        await db.commit()
```

**Remove `_tick()` offline logic** — since `disconnect_agent()` is called on both clean disconnect and heartbeat timeout, the explicit offline marking in `_tick()` is redundant.

### 3.4 `backend/repositories/seat_repo.py`

Add helper:

```python
async def get_all_seat_ids(db: AsyncSession) -> Sequence[str]:
    """Return all seat IDs for startup initialization."""
    result = await db.execute(select(Seat.id))
    return result.scalars().all()
```

---

## 4. Error Handling

| Scenario | Behavior |
|----------|----------|
| DB error during startup init | Log per-seat failure, continue with remaining seats, don't block boot |
| DB error in `_handle_register` | Log, status will sync on next register/heartbeat |
| DB error in `disconnect_agent` | Log, status will sync on next agent connect |
| WebSocket broadcast fails | Log, connection cleaned up by existing logic |

---

## 5. Testing

| Test | Description |
|------|-------------|
| Unit: `initialize_seat_statuses` | Creates N seats, calls init, verifies all `OFFLINE` + broadcasts |
| Unit: `get_all_seat_ids` | Returns all seat IDs |
| Integration: Agent connect | Connect agent → seat status `ONLINE` in DB + dashboard |
| Integration: Agent disconnect | Disconnect agent → seat status `OFFLINE` in DB + dashboard |
| Integration: Heartbeat timeout | Simulate missed PONG → `disconnect_agent` called → seat `OFFLINE` |
| E2E: Server restart with active agent | Start server (seats OFFLINE), connect agent → ONLINE, restart server → OFFLINE, agent reconnects → ONLINE |

---

## 6. Rollout Plan

1. Add `get_all_seat_ids()` to `seat_repo.py`
2. Add `initialize_seat_statuses()` to `startup.py`
3. Wire into `main.py` lifespan
4. Update `ws_manager.py` register/disconnect handlers
5. Remove redundant `_tick()` offline logic
6. Run tests
7. Deploy

---

## 7. Out of Scope

- `UNREACHABLE` status (not used per requirements)
- Periodic reconciliation background task
- WoL counter resets on startup
- Agent provisioning data reset on startup