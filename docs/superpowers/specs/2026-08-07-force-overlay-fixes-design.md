# Force Overlay Fixes + 503 Error Resolution — Design Spec

**Date:** 2026-08-07
**Status:** Approved for Implementation
**Author:** Assistant

---

## 1. Problem Statement

### 1.1 Force Overlay ON State Bug
When "Force Overlay On" is triggered, only a timer flashes in the center and disappears. The full overlay (background + brand + clock + timer + banner + rail + Call Staff button) should be visible. The `minimal` CSS class appears to be stuck ON.

### 1.2 Overlay Dismissal Inconsistency
When overlay is closed via:
- **Force Overlay Off button** → Works correctly (sends `FORCE_OVERLAY_OFF` to agent)
- **Staff override (Ctrl+Shift+O)** → Agent hides overlay locally, but server only updates DB flag; no command sent to agent
- **Reset Override button** → Sends `RESET_OVERRIDE` to agent, but agent handler is a no-op; server updates DB

Only the first path correctly communicates with the agent.

### 1.3 503 Errors on Rapid Toggle
Repeatedly toggling Force Overlay On/Off triggers `503 Service Unavailable` on `POST /api/seats/{id}/overlay`. Concurrently, `GET /api/members` also returns `503` (shared SQLite connection pool exhaustion).

Root cause: Race condition from overlapping rapid-fire requests hitting the same seat resource. SQLite allows only one writer at a time; rapid transactions exceed `busy_timeout=5000ms`.

---

## 2. Solution Overview

Three coordinated fixes:

| Area | Fix |
|------|-----|
| **Server Concurrency** | Per-seat `asyncio.Lock` mutex + `BEGIN IMMEDIATE` transactions + retry logic + increased `busy_timeout` |
| **Agent Consistency** | Staff override sends `FORCE_OVERLAY_OFF`; `RESET_OVERRIDE` handler calls `hideKioskOverlay()` |
| **Overlay Rendering** | Verify `FORCE_OVERLAY_ON` explicitly clears minimal mode |

---

## 3. Detailed Design

### 3.1 Per-Seat Command Mutex

**File:** `backend/services/remote_command_service.py`

```python
# Module-level lock registry
_seat_locks: dict[str, asyncio.Lock] = {}
_seat_locks_lock = asyncio.Lock()

async def _get_seat_lock(seat_id: str) -> asyncio.Lock:
    async with _seat_locks_lock:
        if seat_id not in _seat_locks:
            _seat_locks[seat_id] = asyncio.Lock()
        return _seat_locks[seat_id]

async def force_overlay(db, seat_id, show, staff):
    lock = await _get_seat_lock(seat_id)
    async with lock:
        return await _force_overlay_inner(db, seat_id, show, staff)
```

**Why:** Serializes all overlay commands per seat. Memory: ~1KB/seat. Cleanup on agent disconnect (optional future enhancement).

---

### 3.2 SQLite `BEGIN IMMEDIATE` + Retry Logic

**File:** `backend/core/database.py`

**Option A (preferred): Engine-level isolation**
```python
async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_DB_PATH}",
    echo=False,
    connect_args={"isolation_level": "IMMEDIATE"},
)
```

**Option B: Event hooks (fallback)**
```python
@event.listens_for(async_engine.sync_engine, "connect")
def _set_isolation_level(conn, _):
    conn.isolation_level = None

@event.listens_for(async_engine.sync_engine, "begin")
def _emit_begin_immediate(conn):
    conn.exec_driver_sql("BEGIN IMMEDIATE")
```

**Retry decorator:**
```python
async def _with_retry(coro, retries=3, base_delay=0.1):
    for attempt in range(retries):
        try:
            return await coro
        except OperationalError as e:
            if "database is locked" in str(e) or "SQLITE_BUSY" in str(e):
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, 0.05))
            else:
                raise
```

Apply to `_force_overlay_inner` transaction block.

---

### 3.3 Increase `busy_timeout`

**File:** `backend/core/database.py`

```python
cursor.execute("PRAGMA busy_timeout = 15000")  # 15s instead of 5s
```

---

### 3.4 Fix Staff Override Path

**File:** `backend/core/ws_manager.py` — `_handle_staff_override`

After clearing `overlay_forced` in DB, send `FORCE_OVERLAY_OFF` to agent:

```python
# Existing code clears overlay_forced...
await seat_service.set_overlay_forced(db, seat_id, False)

# ADD: Notify agent to hide overlay
try:
    await manager.send_to_agent(seat_id, {
        "type": Msg.FORCE_OVERLAY_OFF,
        "payload": {}
    })
except AgentOfflineError:
    pass  # Agent already offline; overlay_forced already cleared in DB
```

---

### 3.5 Fix RESET_OVERRIDE Handler

**File:** `agent/src/main/ws/commands.ts`

```typescript
RESET_OVERRIDE(_payload) {
    // Previously a no-op; now hide the overlay
    platform.hideKioskOverlay();
}
```

---

### 3.6 Force Overlay ON Minimal Mode

**File:** `agent/src/main/ws/commands.ts` — `FORCE_OVERLAY_ON` handler

Already sends `overlay:set-minimal: false` via `platform.showKioskOverlay()`. Add defensive explicit call:

```typescript
FORCE_OVERLAY_ON(payload) {
    platform.showKioskOverlay({
        cafeName: deps.getCafeName?.() || 'Arcade',
        announcements: [],
        callStaffEnabled: true,
        sessionActive: !!payload.session_id,
        eventBanner: deps.getEventBanner?.() || '',
        serverUrl: deps.serverUrl,
        seatId: deps.seatId,
        agentSecret: deps.agentSecret,
    });
    // Explicitly ensure minimal mode is OFF
    platform.sendToOverlayAndHud('overlay:set-minimal', false);
}
```

**Verify CSS:** Check `.kiosk-overlay.minimal` class in renderer CSS doesn't override visibility incorrectly.

---

## 4. Data Flow

```
Frontend (SeatActionModal)
    └─ POST /api/seats/{id}/overlay {show: true}
           └─ force_overlay(seat_id, true)
                  └─ _get_seat_lock(seat_id) → asyncio.Lock
                         └─ async with lock:
                                ├─ _get_seat_or_404
                                ├─ _send_to_agent_or_503(FORCE_OVERLAY_ON)
                                ├─ DB updates (session pause, seat status, overlay_forced)
                                ├─ audit log
                                └─ commit (with BEGIN IMMEDIATE + retry)
```

**Staff Override Path:**
```
Agent (Ctrl+Shift+O + PIN)
    └─ STAFF_OVERRIDE WebSocket message
           └─ _handle_staff_override
                  ├─ Broadcast ALERT to dashboards
                  ├─ set_overlay_forced(db, seat_id, False)
                  ├─ Audit log
                  └─ send_to_agent(FORCE_OVERLAY_OFF)  ← NEW
```

---

## 5. Error Handling

| Scenario | Behavior |
|----------|----------|
| Agent offline during force_overlay | 503 returned immediately (existing); mutex released |
| SQLite lock timeout (15s) | Retry 3x with exponential backoff; then 503 |
| Staff override + agent offline | DB flag cleared; agent command skipped gracefully |
| Rapid concurrent toggles | Serialized by per-seat mutex; each waits its turn |

---

## 6. Testing Strategy

### 6.1 Unit Tests
- `test_seat_lock_serializes_commands`: Mock lock, verify sequential execution
- `test_retry_on_sqlite_busy`: Simulate `OperationalError`, verify retry logic
- `test_staff_override_sends_force_overlay_off`: Mock `send_to_agent`, verify call

### 6.2 Integration Tests
- `test_rapid_toggle_10_times`: 10 rapid POSTs to `/overlay`; all succeed (204)
- `test_bulk_overlay_concurrent_with_individual`: Bulk + single toggles don't deadlock
- `test_staff_override_dismisses_overlay`: Verify agent receives `FORCE_OVERLAY_OFF`

### 6.3 Agent E2E Tests
- Force Overlay On → verify full overlay visible (not minimal)
- Force Overlay Off → verify minimal mode (Call Staff only)
- Staff Override → verify minimal mode
- Reset Override → verify minimal mode

---

## 7. Files to Modify

| File | Changes |
|------|---------|
| `backend/services/remote_command_service.py` | Add `_seat_locks`, `_get_seat_lock`, wrap `force_overlay` |
| `backend/core/database.py` | `BEGIN IMMEDIATE` + retry helper + `busy_timeout=15000` |
| `backend/core/ws_manager.py` | `_handle_staff_override` sends `FORCE_OVERLAY_OFF` |
| `agent/src/main/ws/commands.ts` | `RESET_OVERRIDE` calls `hideKioskOverlay()`; `FORCE_OVERLAY_ON` explicit `set-minimal: false` |
| `backend/tests/test_remote_commands.py` | Add mutex, retry, staff override tests |
| `backend/tests/test_seat_router.py` | Add rapid toggle integration test |

---

## 8. Rollback Plan

If issues arise:
1. Revert `database.py` isolation level change (low risk)
2. Disable mutex by setting `_seat_locks = {}` and skipping lock acquisition
3. Revert `ws_manager.py` staff override addition (safe — agent ignores unknown commands)
4. Agent changes are additive — no rollback needed

---

## 9. Future Considerations

- **Lock cleanup:** Add `_seat_locks.pop(seat_id, None)` in `disconnect_agent` when agent count is high
- **Metrics:** Add lock wait time histogram for monitoring
- **Scale:** If > 500 seats, consider optimistic locking (version column) instead of mutex

---

## 10. Acceptance Criteria

- [ ] Force Overlay On shows full overlay (no timer flash)
- [ ] Force Overlay Off → minimal mode (Call Staff only)
- [ ] Staff Override → minimal mode (Call Staff only)
- [ ] Reset Override → minimal mode (Call Staff only)
- [ ] 10 rapid toggles → all return 204 (no 503)
- [ ] Concurrent bulk + individual toggles → no deadlock/timeout
- [ ] GET /api/members remains responsive during overlay toggles
