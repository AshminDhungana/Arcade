# Seat Online/Offline Status Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement automatic seat online/offline status tracking so the dashboard accurately reflects which gaming stations are currently connected to the server via their agents.

**Architecture:** Centralized startup initialization sets all seats to OFFLINE. WebSocket handlers update status to ONLINE on agent REGISTER and OFFLINE on agent disconnect (clean or heartbeat timeout). All changes broadcast via SEAT_UPDATED WebSocket events to dashboards.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), WebSocket, pytest

## Global Constraints

- Startup: All seats initialized to OFFLINE on server boot
- Agent connects (REGISTER): Seat → ONLINE, broadcast SEAT_UPDATED
- Agent disconnects (clean or heartbeat timeout): Seat → OFFLINE, broadcast SEAT_UPDATED
- Use existing `seat.status` column (enum includes ONLINE, OFFLINE)
- No UNREACHABLE status, no periodic reconciliation, no WoL counter resets
- Error handling: Log failures, don't block boot, status syncs on next event

---

### Task 1: Add `get_all_seat_ids()` to seat_repo.py

**Files:**
- Modify: `backend/repositories/seat_repo.py`
- Test: `backend/tests/test_seat_repo.py` (create if missing)

**Interfaces:**
- Consumes: `db: AsyncSession`
- Produces: `Sequence[str]` — all seat IDs

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_seat_repo.py
import pytest
from backend.repositories import seat_repo
from backend.core.database import AsyncSessionLocal
from backend.models import Seat


@pytest.mark.asyncio
async def test_get_all_seat_ids():
    async with AsyncSessionLocal() as db:
        # Create test seats
        seat1 = await seat_repo.create(db, name="Seat 1", zone_id="zone1")
        seat2 = await seat_repo.create(db, name="Seat 2", zone_id="zone1")
        await db.commit()

        # Call function
        ids = await seat_repo.get_all_seat_ids(db)

        assert seat1.id in ids
        assert seat2.id in ids
        assert len(ids) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_seat_repo.py::test_get_all_seat_ids -v`
Expected: FAIL with "AttributeError: module 'backend.repositories.seat_repo' has no attribute 'get_all_seat_ids'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/repositories/seat_repo.py (add at end of file)

async def get_all_seat_ids(db: AsyncSession) -> Sequence[str]:
    """Return all seat IDs for startup initialization."""
    result = await db.execute(select(Seat.id))
    return result.scalars().all()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_seat_repo.py::test_get_all_seat_ids -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/repositories/seat_repo.py backend/tests/test_seat_repo.py
git commit -m "feat: add get_all_seat_ids to seat_repo"
```

---

### Task 2: Add `initialize_seat_statuses()` to startup.py

**Files:**
- Modify: `backend/core/startup.py`
- Test: `backend/tests/test_startup.py` (create if missing)

**Interfaces:**
- Consumes: None
- Produces: None (side effects: DB updates + WebSocket broadcasts)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_startup.py
import pytest
from backend.core.startup import initialize_seat_statuses
from backend.core.database import AsyncSessionLocal
from backend.models import Seat, SeatStatus
from backend.repositories import seat_repo


@pytest.mark.asyncio
async def test_initialize_seat_statuses_sets_all_offline():
    async with AsyncSessionLocal() as db:
        # Create test seats with various statuses
        seat1 = await seat_repo.create(db, name="Seat 1", zone_id="zone1")
        seat2 = await seat_repo.create(db, name="Seat 2", zone_id="zone1")
        seat1.status = SeatStatus.ONLINE
        seat2.status = SeatStatus.IN_USE
        await db.commit()

        # Call function
        await initialize_seat_statuses()

        # Verify all seats are OFFLINE
        for seat_id in [seat1.id, seat2.id]:
            refreshed = await db.get(Seat, seat_id)
            assert refreshed.status == SeatStatus.OFFLINE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_startup.py::test_initialize_seat_statuses_sets_all_offline -v`
Expected: FAIL with "AttributeError: module 'backend.core.startup' has no attribute 'initialize_seat_statuses'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/core/startup.py (add after boot_all_seats function)

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
            try:
                await seat_repo.update_status(db, seat_id, SeatStatus.OFFLINE)
                # Broadcast to dashboards
                seat = await db.get(Seat, seat_id)
                if seat:
                    await ws_manager.broadcast_to_dashboards("seat_updated", {
                        "seat_id": seat_id,
                        "status": "OFFLINE",
                    })
            except Exception as e:
                # Log per-seat failure, continue with remaining seats
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to initialize status for seat %s: %s", seat_id, e
                )
        await db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_startup.py::test_initialize_seat_statuses_sets_all_offline -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/startup.py backend/tests/test_startup.py
git commit -m "feat: add initialize_seat_statuses to startup"
```

---

### Task 3: Wire `initialize_seat_statuses()` into main.py lifespan

**Files:**
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `initialize_seat_statuses()` from startup module
- Produces: None (lifespan side effect)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_main_lifespan.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.main import lifespan
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_lifespan_calls_initialize_seat_statuses():
    app = FastAPI(lifespan=lifespan)
    
    with patch("backend.main.initialize_seat_statuses", new_callable=AsyncMock) as mock_init:
        async with lifespan(app):
            pass
        
        mock_init.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_main_lifespan.py::test_lifespan_calls_initialize_seat_statuses -v`
Expected: FAIL - `initialize_seat_statuses` not called in lifespan

- [ ] **Step 3: Write minimal implementation**

```python
# backend/main.py - modify lifespan function, add import at top

# Add import (after line 52):
from backend.core.startup import (
    boot_all_seats,
    initialize_seat_statuses,  # ADD THIS
    recover_active_sessions,
    run_migrations,
)

# In lifespan function, after run_migrations() (around line 81):
    await run_migrations()
    await initialize_seat_statuses()  # ADD THIS LINE
    await recover_active_sessions()
    await boot_all_seats()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_main_lifespan.py::test_lifespan_calls_initialize_seat_statuses -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_main_lifespan.py
git commit -m "feat: wire initialize_seat_statuses into lifespan"
```

---

### Task 4: Update `_handle_register()` in ws_manager.py to set seat ONLINE

**Files:**
- Modify: `backend/core/ws_manager.py`
- Test: `backend/tests/test_ws_manager.py` (create if missing)

**Interfaces:**
- Consumes: `seat_id: str`
- Produces: None (side effects: DB update + WebSocket broadcast)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ws_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.core.ws_manager import WebSocketManager
from backend.core.database import AsyncSessionLocal
from backend.models import Seat, SeatStatus
from backend.repositories import seat_repo


@pytest.mark.asyncio
async def test_handle_register_sets_seat_online():
    manager = WebSocketManager()
    
    # Setup: create a seat in OFFLINE status
    async with AsyncSessionLocal() as db:
        seat = await seat_repo.create(db, name="Test Seat", zone_id="zone1")
        seat.status = SeatStatus.OFFLINE
        await db.commit()
        seat_id = seat.id
    
    # Mock websocket
    mock_ws = AsyncMock()
    
    # Call _handle_register
    with patch("backend.core.ws_manager.manager", manager):
        result = await manager._handle_register(seat_id, {
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "hostname": "test-pc"
        })
    
    # Verify seat is now ONLINE
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.ONLINE
    
    # Verify response
    assert result["type"] == "REGISTERED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ws_manager.py::test_handle_register_sets_seat_online -v`
Expected: FAIL - seat status not updated to ONLINE

- [ ] **Step 3: Write minimal implementation**

```python
# backend/core/ws_manager.py - modify _handle_register method (around line 331)

async def _handle_register(
    self, seat_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Handle agent REGISTER message.

    Accepts the REGISTER payload and broadcasts the agent's online status
    to all dashboard clients.
    """
    mac_address = payload.get("mac_address", "")
    hostname = payload.get("hostname", "")
    
    # Update seat status to ONLINE in database
    from backend.core.database import AsyncSessionLocal
    from backend.repositories import seat_repo
    from backend.models._enums import SeatStatus
    
    async with AsyncSessionLocal() as db:
        await seat_repo.update_status(db, seat_id, SeatStatus.ONLINE)
        await db.commit()

    await self.broadcast_to_dashboards(
        Msg.SEAT_UPDATED,
        {
            "seat_id": seat_id,
            "status": "ONLINE",
            "mac_address": mac_address,
            "hostname": hostname,
        },
    )
    # ... rest of existing code unchanged ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ws_manager.py::test_handle_register_sets_seat_online -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/ws_manager.py backend/tests/test_ws_manager.py
git commit -m "feat: update _handle_register to set seat ONLINE"
```

---

### Task 5: Update `disconnect_agent()` in ws_manager.py to set seat OFFLINE

**Files:**
- Modify: `backend/core/ws_manager.py`
- Test: `backend/tests/test_ws_manager.py`

**Interfaces:**
- Consumes: `seat_id: str`
- Produces: None (side effects: DB update + WebSocket broadcast)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ws_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.core.ws_manager import WebSocketManager
from backend.core.database import AsyncSessionLocal
from backend.models import Seat, SeatStatus
from backend.repositories import seat_repo


@pytest.mark.asyncio
async def test_disconnect_agent_sets_seat_offline():
    manager = WebSocketManager()
    
    # Setup: create a seat in ONLINE status
    async with AsyncSessionLocal() as db:
        seat = await seat_repo.create(db, name="Test Seat", zone_id="zone1")
        seat.status = SeatStatus.ONLINE
        await db.commit()
        seat_id = seat.id
    
    # Mock websocket connection
    mock_ws = AsyncMock()
    manager.agent_connections[seat_id] = mock_ws
    
    # Call disconnect_agent
    await manager.disconnect_agent(seat_id)
    
    # Verify seat is now OFFLINE
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.OFFLINE
    
    # Verify connection cleaned up
    assert seat_id not in manager.agent_connections
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ws_manager.py::test_disconnect_agent_sets_seat_offline -v`
Expected: FAIL - seat status not updated to OFFLINE

- [ ] **Step 3: Write minimal implementation**

```python
# backend/core/ws_manager.py - modify disconnect_agent method (around line 217)

async def disconnect_agent(self, seat_id: str) -> None:
    # Cancel any pending screenshot futures for this seat
    async with self._screenshot_lock:
        for req_id, req_seat in list(self._screenshot_seat.items()):
            if req_seat == seat_id:
                fut = self._screenshot_waiters.pop(req_id, None)
                self._screenshot_seat.pop(req_id, None)
                if fut is not None and not fut.done():
                    fut.cancel()
    async with self._lock:
        self._pending_pongs.discard(seat_id)
        self.agent_connections.pop(seat_id, None)
    
    # Update seat status to OFFLINE in database
    from backend.core.database import AsyncSessionLocal
    from backend.repositories import seat_repo
    from backend.models._enums import SeatStatus
    
    async with AsyncSessionLocal() as db:
        try:
            await seat_repo.update_status(db, seat_id, SeatStatus.OFFLINE)
            await db.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to set seat %s to OFFLINE on disconnect: %s", seat_id, e
            )
    
    # Broadcast OFFLINE status to dashboards
    await self.broadcast_to_dashboards(
        Msg.SEAT_UPDATED,
        {
            "seat_id": seat_id,
            "status": "OFFLINE",
        },
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ws_manager.py::test_disconnect_agent_sets_seat_offline -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/ws_manager.py backend/tests/test_ws_manager.py
git commit -m "feat: update disconnect_agent to set seat OFFLINE"
```

---

### Task 6: Remove redundant offline logic from `_tick()` in ws_manager.py

**Files:**
- Modify: `backend/core/ws_manager.py`

**Interfaces:**
- Consumes: None
- Produces: None (removes dead code)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ws_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.core.ws_manager import WebSocketManager


@pytest.mark.asyncio
async def test_tick_does_not_broadcast_offline():
    """Verify _tick no longer broadcasts OFFLINE status (handled by disconnect_agent)."""
    manager = WebSocketManager()
    manager.broadcast_to_dashboards = AsyncMock()
    
    # Add a fake agent connection
    mock_ws = AsyncMock()
    manager.agent_connections["seat1"] = mock_ws
    manager._pending_pongs.add("seat1")
    
    # Call _tick
    await manager._tick()
    
    # Verify no OFFLINE broadcast was sent
    offline_calls = [
        call for call in manager.broadcast_to_dashboards.call_args_list
        if call.kwargs.get("payload", {}).get("status") == "OFFLINE"
    ]
    assert len(offline_calls) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_ws_manager.py::test_tick_does_not_broadcast_offline -v`
Expected: FAIL - _tick still broadcasts OFFLINE

- [ ] **Step 3: Write minimal implementation**

```python
# backend/core/ws_manager.py - modify _tick method (around line 582)

async def _tick(self) -> None:
    # Step 1: Disconnect agents who didn't PONG from the PREVIOUS tick
    expired = list(self._pending_pongs)
    for seat_id in expired:
        ws = self.agent_connections.pop(seat_id, None)
        if ws is not None:
            try:
                await ws.close(code=1001, reason="heartbeat timeout")
            except Exception:
                import logging
                logging.getLogger(__name__).debug(
                    "Failed to close agent websocket on heartbeat timeout"
                )
            # disconnect_agent() will be called by the WebSocket close handler
            # which handles OFFLINE status update and broadcast

    # Step 2: Send PING to all current agents
    current_agents = list(self.agent_connections.items())
    self._pending_pongs.clear()
    for seat_id, ws in current_agents:
        try:
            await ws.send_json(ws_envelope(Msg.PING, {}))
            self._pending_pongs.add(seat_id)
        except Exception:
            self.agent_connections.pop(seat_id, None)
            # disconnect_agent() will handle OFFLINE status
            from backend.core.database import AsyncSessionLocal
            from backend.repositories import seat_repo
            from backend.models._enums import SeatStatus
            async with AsyncSessionLocal() as db:
                try:
                    await seat_repo.update_status(db, seat_id, SeatStatus.OFFLINE)
                    await db.commit()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Failed to set seat %s to OFFLINE on send error: %s", seat_id, e
                    )
            await self.broadcast_to_dashboards(
                Msg.SEAT_UPDATED,
                {"seat_id": seat_id, "status": "OFFLINE"},
            )
```

Wait - the disconnect_agent is called by the WebSocket close handler. Let me check how the close handler works. Actually, looking at the code, when a websocket closes, it's handled by the WebSocket route, not automatically by the manager. The `_tick` method manually closes the websocket but doesn't call `disconnect_agent`. Let me fix this.

Actually, looking more carefully at the code, the `disconnect_agent` is called explicitly in various places. In `_tick`, when an agent times out, it closes the websocket but doesn't call `disconnect_agent`. We need to call `disconnect_agent` for expired agents.

Let me revise:

```python
# backend/core/ws_manager.py - modify _tick method (around line 582)

async def _tick(self) -> None:
    # Step 1: Disconnect agents who didn't PONG from the PREVIOUS tick
    expired = list(self._pending_pongs)
    for seat_id in expired:
        # Call disconnect_agent which handles cleanup, DB update, and broadcast
        await self.disconnect_agent(seat_id)

    # Step 2: Send PING to all current agents
    current_agents = list(self.agent_connections.items())
    self._pending_pongs.clear()
    for seat_id, ws in current_agents:
        try:
            await ws.send_json(ws_envelope(Msg.PING, {}))
            self._pending_pongs.add(seat_id)
        except Exception:
            # Connection failed, disconnect_agent will handle cleanup
            await self.disconnect_agent(seat_id)
```

This is cleaner - just call disconnect_agent which handles everything.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ws_manager.py::test_tick_does_not_broadcast_offline -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/ws_manager.py backend/tests/test_ws_manager.py
git commit -m "refactor: remove redundant offline logic from _tick, use disconnect_agent"
```

---

### Task 7: Integration test - full online/offline cycle

**Files:**
- Test: `backend/tests/test_seat_status_integration.py`

**Interfaces:**
- Tests full flow: startup → agent connect → agent disconnect

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_seat_status_integration.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.core.startup import initialize_seat_statuses
from backend.core.ws_manager import WebSocketManager
from backend.core.database import AsyncSessionLocal
from backend.models import Seat, SeatStatus
from backend.repositories import seat_repo


@pytest.mark.asyncio
async def test_full_online_offline_cycle():
    """Test: startup sets OFFLINE → register sets ONLINE → disconnect sets OFFLINE"""
    async with AsyncSessionLocal() as db:
        # Clean slate
        await db.execute("DELETE FROM seats")
        await db.commit()
        
        # Create test seat
        seat = await seat_repo.create(db, name="Integration Seat", zone_id="zone1")
        seat.status = SeatStatus.ONLINE  # Simulate previous state
        await db.commit()
        seat_id = seat.id
    
    # 1. Startup initialization - should set to OFFLINE
    await initialize_seat_statuses()
    
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.OFFLINE
    
    # 2. Agent connects - REGISTER should set ONLINE
    manager = WebSocketManager()
    
    with patch("backend.core.ws_manager.manager", manager):
        await manager._handle_register(seat_id, {
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "hostname": "test-pc"
        })
    
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.ONLINE
    
    # 3. Agent disconnects - should set OFFLINE
    await manager.disconnect_agent(seat_id)
    
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.OFFLINE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_seat_status_integration.py::test_full_online_offline_cycle -v`
Expected: FAIL (one or more steps not implemented yet)

- [ ] **Step 3: Run test after all previous tasks complete**

Run: `pytest backend/tests/test_seat_status_integration.py::test_full_online_offline_cycle -v`
Expected: PASS (after Tasks 1-6 complete)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_seat_status_integration.py
git commit -m "test: add integration test for seat online/offline cycle"
```

---

### Task 8: Run full test suite and verify no regressions

**Files:**
- No new files

**Interfaces:**
- Runs all tests

- [ ] **Step 1: Run all backend tests**

Run: `pytest backend/tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run lint/typecheck if available**

Run: `ruff check backend/` (or project's lint command)
Expected: No errors

Run: `mypy backend/` (or project's typecheck command)
Expected: No errors

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve any lint/typecheck issues"
```

---

## Execution Notes

**Order of execution:** Tasks 1-6 can be done in parallel for Tasks 1, 2, 3, 4, 5 (independent). Task 6 depends on Task 5. Task 7 depends on Tasks 1-6. Task 8 is final.

**Total estimated time:** ~30-45 minutes for all tasks

**Key files modified:**
1. `backend/repositories/seat_repo.py` - add `get_all_seat_ids()`
2. `backend/core/startup.py` - add `initialize_seat_statuses()`
3. `backend/main.py` - wire into lifespan
4. `backend/core/ws_manager.py` - update `_handle_register`, `disconnect_agent`, `_tick`

**Tests added:**
- `backend/tests/test_seat_repo.py` - repo helper
- `backend/tests/test_startup.py` - startup init
- `backend/tests/test_main_lifespan.py` - lifespan wiring
- `backend/tests/test_ws_manager.py` - WS handler updates
- `backend/tests/test_seat_status_integration.py` - full cycle