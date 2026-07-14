"""WebSocket connection manager for Arcade.

Manages two classes of WebSocket connections:

- **Dashboards**: React front-end staff dashboard clients.
- **Agents**: Electron agent running on each gaming PC.

All messages use a standard JSON envelope (SDD §9.2)::

    {"type": "EVENT_TYPE", "payload": {...}, "timestamp": "2026-06-01T10:00:00Z"}
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket

from backend.core.config import get_config
from backend.core.database import AsyncSessionLocal

# ---------------------------------------------------------------------------
# Constants  (SDD §9.1)
# ---------------------------------------------------------------------------

HEARTBEAT_INTERVAL = 30.0
HEARTBEAT_TIMEOUT = 10.0
MAX_MESSAGE_SIZE = 5 * 1024 * 1024  # 5 MB (enforced at uvicorn level)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AgentOfflineError(Exception):
    """Raised when *send_to_agent* targets an offline agent."""

    def __init__(self, seat_id: str) -> None:
        self.seat_id = seat_id
        super().__init__(f"Agent for seat {seat_id} is offline")


# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------


def ws_envelope(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return a standard WebSocket message envelope."""
    return {
        "type": type_,
        "payload": payload,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# Reconciliation (lifted from ARCH-06 validation spike)
# ---------------------------------------------------------------------------


@dataclass
class ReconcileResult:
    """Outcome of a server–agent elapsed-time reconciliation."""

    chosen_elapsed_seconds: float
    drift: float
    action: str
    reason: str
    tolerance_seconds: float


def server_anchor_elapsed(
    started_at: datetime,
    total_paused_seconds: float,
    now: datetime,
) -> float:
    """SAE = (now - started_at) - total_paused_seconds, in seconds."""
    elapsed = (now - started_at).total_seconds() - total_paused_seconds
    return max(0.0, elapsed)


def reconcile(
    sae_seconds: float,
    ale_seconds: float,
    tolerance: float = 5.0,
) -> ReconcileResult:
    """Reconcile server-anchor elapsed with agent-local elapsed."""
    drift = sae_seconds - ale_seconds
    if abs(drift) <= tolerance:
        return ReconcileResult(
            chosen_elapsed_seconds=sae_seconds,
            drift=drift,
            action="ACCEPT_SAE",
            reason="agent local elapsed within tolerance of server anchor",
            tolerance_seconds=tolerance,
        )
    direction = "lower" if ale_seconds < sae_seconds else "higher"
    return ReconcileResult(
        chosen_elapsed_seconds=ale_seconds,
        drift=drift,
        action="ADOPT_ALE",
        reason=(
            f"agent local elapsed {direction} than server anchor by "
            f"{abs(drift):.1f}s beyond {tolerance:.0f}s tolerance; "
            "deferring to agent"
        ),
        tolerance_seconds=tolerance,
    )


# ---------------------------------------------------------------------------
# Message type constants (SDD §9.3)
# ---------------------------------------------------------------------------


class Msg:
    # Agent -> Server
    REGISTER = "REGISTER"
    SYNC = "SYNC"
    HEALTH = "HEALTH"
    STAFF_OVERRIDE = "STAFF_OVERRIDE"
    STAFF_ALERT = "STAFF_ALERT"
    PONG = "PONG"
    SCREENSHOT_RESULT = "SCREENSHOT_RESULT"

    # Server -> Agent
    PING = "PING"

    # Server -> Dashboard
    SEAT_UPDATED = "seat_updated"
    HEALTH_UPDATE = "health_update"
    ANNOUNCEMENT = "announcement"
    ALERT = "alert"

    # Server -> Agent (remote commands)
    SHOW_MESSAGE = "SHOW_MESSAGE"
    TAKE_SCREENSHOT = "TAKE_SCREENSHOT"
    RESTART = "RESTART"
    SHUTDOWN = "SHUTDOWN"


# ---------------------------------------------------------------------------
# WebSocketManager
# ---------------------------------------------------------------------------


class WebSocketManager:
    """Manages dashboard and agent WebSocket connections.

    This class is a singleton accessed via the module-level ``manager``
    instance. FastAPI lifespan should call ``await manager.close_all()``
    on shutdown.
    """

    def __init__(self) -> None:
        self.dashboard_connections: list[WebSocket] = []
        self.agent_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._pending_pongs: set[str] = set()
        self._health_data: dict[str, dict[str, Any]] = {}
        # Screenshot request/response correlation (Task 1)
        self._screenshot_waiters: dict[str, asyncio.Future[bytes]] = {}
        self._screenshot_seat: dict[str, str] = {}  # request_id -> seat_id
        self._screenshot_lock = asyncio.Lock()

    # --- Dashboards --------------------------------------------------------

    async def connect_dashboard(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.dashboard_connections.append(ws)
        await self._start_heartbeat()

    async def disconnect_dashboard(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self.dashboard_connections:
                self.dashboard_connections.remove(ws)

    # --- Agents ------------------------------------------------------------

    async def connect_agent(self, seat_id: str, secret: str, ws: WebSocket) -> bool:
        config = get_config()
        expected = config.agent_secrets.get(seat_id)
        if expected is None or expected != secret:
            await ws.close(code=1008, reason="Invalid agent secret")
            return False
        await ws.accept()
        async with self._lock:
            self.agent_connections[seat_id] = ws
            self._pending_pongs.discard(seat_id)
        await self._start_heartbeat()
        return True

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

    # --- Sending ------------------------------------------------------------

    async def send_to_agent(self, seat_id: str, command: dict[str, Any]) -> None:
        ws = self.agent_connections.get(seat_id)
        if ws is None:
            raise AgentOfflineError(seat_id)
        message = ws_envelope(command["type"], command.get("payload", {}))
        await ws.send_json(message)

    # --- Screenshot request/response correlation ----------------------

    async def wait_for_screenshot(
        self, request_id: str, *, seat_id: str, timeout: float = 3.0
    ) -> bytes:
        """Register a future for *request_id* and await the agent's result.

        Records ``seat_id`` in ``_screenshot_seat`` so a disconnect can cancel
        the pending future.

        Raises:
            asyncio.TimeoutError: If no ``SCREENSHOT_RESULT`` arrives in time.
            asyncio.CancelledError: If the agent disconnects (future cancelled).
        """
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[bytes] = loop.create_future()
        async with self._screenshot_lock:
            self._screenshot_waiters[request_id] = fut
            self._screenshot_seat[request_id] = seat_id
        try:
            return await asyncio.wait_for(fut, timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):  # noqa: UP041
            async with self._screenshot_lock:
                self._screenshot_waiters.pop(request_id, None)
                self._screenshot_seat.pop(request_id, None)
            raise

    async def resolve_screenshot(self, request_id: str, data: bytes) -> None:
        """Resolve the pending future for *request_id* with JPEG *data*."""
        async with self._screenshot_lock:
            fut = self._screenshot_waiters.pop(request_id, None)
            self._screenshot_seat.pop(request_id, None)
        if fut is not None and not fut.done():
            fut.set_result(data)

    async def broadcast_to_dashboards(
        self, event: str, payload: dict[str, Any]
    ) -> None:
        text = json.dumps(ws_envelope(event, payload))
        disconnected: list[WebSocket] = []
        async with self._lock:
            for ws in list(self.dashboard_connections):
                try:
                    await ws.send_text(text)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                if ws in self.dashboard_connections:
                    self.dashboard_connections.remove(ws)

    # --- Agent message dispatch --------------------------------------------

    async def handle_agent_message(  # noqa: C901
        self, seat_id: str, message: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Dispatch an incoming agent message to the appropriate handler.

        Returns a response dict to be sent back to the agent, or ``None`` if no
        response should be sent (e.g., for SCREENSHOT_RESULT).
        """
        msg_type = message.get("type", "").upper()
        payload = message.get("payload", {})

        match msg_type:
            case "REGISTER":
                return await self._handle_register(seat_id, payload)
            case "SYNC":
                return await self._handle_sync(seat_id, payload)
            case "HEALTH":
                return await self._handle_health(seat_id, payload)
            case "STAFF_OVERRIDE":
                return await self._handle_staff_override(seat_id, payload)
            case "STAFF_ALERT":
                return await self._handle_staff_alert(seat_id, payload)
            case "PONG":
                await self.handle_pong(seat_id)
                return {"type": "PONG_ACK"}
            case "SCREENSHOT_RESULT":
                await self._handle_screenshot_response(payload)
                return None
            case _:
                return {"type": "ERROR", "message": f"Unknown message type: {msg_type}"}

    async def _handle_register(
        self, seat_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle agent REGISTER message.

        Accepts the REGISTER payload and broadcasts the agent's online status
        to all dashboard clients.
        """
        mac_address = payload.get("mac_address", "")
        hostname = payload.get("hostname", "")
        await self.broadcast_to_dashboards(
            Msg.SEAT_UPDATED,
            {
                "seat_id": seat_id,
                "status": "ONLINE",
                "mac_address": mac_address,
                "hostname": hostname,
            },
        )
        # Notify WoL service that an agent registered (may be a WoL success)
        from backend.services.wol_service import wol_success_callback as _wol_callback

        asyncio.create_task(_wol_callback(seat_id))
        return {
            "type": "REGISTERED",
            "seat_id": seat_id,
            "cafe_name": get_config().cafe_name,
        }

    async def _handle_sync(
        self, seat_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle agent SYNC message after reconnect.

        Fetches the session from the database, computes server anchor elapsed,
        reconciles with agent-local elapsed, and returns the chosen value.
        """
        session_id = payload.get("session_id")
        local_elapsed = float(payload.get("local_elapsed_seconds", 0.0))

        if not session_id:
            return {
                "type": "SYNC_ACK",
                "session_id": None,
                "chosen_elapsed_seconds": 0,
                "error": "Missing session_id in SYNC payload",
            }

        # --- DB + Reconciliation ---
        from backend.models import SessionStatus
        from backend.repositories import session_repo

        chosen_seconds = local_elapsed
        sae_seconds = 0.0
        drift = local_elapsed
        action = "NO_SESSION"

        try:
            async with AsyncSessionLocal() as db:
                session = await session_repo.get_by_id(db, session_id)
                if session is not None and session.status == SessionStatus.ACTIVE:
                    started_at = session.started_at
                    total_paused = float(session.total_paused_seconds or 0)
                    now = datetime.now(UTC)
                    sae_seconds = server_anchor_elapsed(started_at, total_paused, now)
                    result = reconcile(sae_seconds, local_elapsed)
                    chosen_seconds = result.chosen_elapsed_seconds
                    drift = result.drift
                    action = result.action
        except Exception:
            logger.warning(
                "Failed to reconcile SYNC for session %s, "
                "falling back to agent elapsed",
                session_id,
                exc_info=True,
            )
            chosen_seconds = local_elapsed

        # --- Broadcast to dashboards ---
        await self.broadcast_to_dashboards(
            Msg.SEAT_UPDATED,
            {
                "seat_id": seat_id,
                "status": "SYNCED",
                "session_id": session_id,
                "local_elapsed_seconds": local_elapsed,
                "server_anchor_elapsed": sae_seconds,
                "chosen_elapsed_seconds": chosen_seconds,
                "drift": drift,
                "action": action,
            },
        )

        return {
            "type": "SYNC_ACK",
            "session_id": session_id,
            "chosen_elapsed_seconds": chosen_seconds,
            "server_anchor_elapsed": sae_seconds,
            "drift": drift,
            "action": action,
        }

    async def _handle_health(
        self, seat_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle agent HEALTH message.

        Stores health metrics in memory and broadcasts to all dashboards.
        """
        self._health_data[seat_id] = payload
        await self.broadcast_to_dashboards(
            Msg.HEALTH_UPDATE,
            {"seat_id": seat_id, **payload},
        )
        return {"type": "HEALTH_ACK"}

    async def _handle_staff_override(
        self, seat_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle agent STAFF_OVERRIDE message.

        Broadcasts an alert to all dashboard clients.
        """
        await self.broadcast_to_dashboards(
            Msg.ALERT,
            {
                "type": "STAFF_OVERRIDE",
                "seat_id": seat_id,
                **payload,
            },
        )
        return {"type": "STAFF_OVERRIDE_ACK"}

    async def _handle_staff_alert(
        self, seat_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle agent STAFF_ALERT message.

        Broadcasts an ``ALERT`` to all dashboard clients so staff see the
        call, and acknowledges the agent.
        """
        await self.broadcast_to_dashboards(
            Msg.ALERT,
            {"type": "STAFF_ALERT", "seat_id": seat_id, **payload},
        )
        return {"type": "STAFF_ALERT_ACK"}

    async def _handle_screenshot_response(self, payload: dict[str, Any]) -> None:
        """Decode and resolve an incoming agent screenshot result.

        Returns ``None`` — no ack is sent back to the agent for screenshots.
        """
        request_id = payload.get("request_id")
        if not request_id:
            logger.warning("SCREENSHOT_RESULT missing request_id; dropping")
            return None
        image_b64 = payload.get("image_base64", "")
        try:
            data = base64.b64decode(image_b64, validate=True)
        except Exception:
            logger.warning("SCREENSHOT_RESULT had invalid base64; dropping")
            data = b""
        await self.resolve_screenshot(request_id, data)
        return None

    # --- Heartbeat ----------------------------------------------------------

    async def handle_pong(self, seat_id: str) -> None:
        """Mark *seat_id* as having responded to the most recent PING."""
        self._pending_pongs.discard(seat_id)

    # --- Lifecycle ----------------------------------------------------------

    async def _start_heartbeat(self) -> None:
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self._tick()
            except asyncio.CancelledError:
                break

    async def _tick(self) -> None:
        # Step 1: Disconnect agents who didn't PONG from the PREVIOUS tick
        expired = list(self._pending_pongs)
        for seat_id in expired:
            ws = self.agent_connections.pop(seat_id, None)
            if ws is not None:
                try:
                    await ws.close(code=1001, reason="heartbeat timeout")
                except Exception:
                    logger.debug("Failed to close agent websocket on heartbeat timeout")

        # Step 2: Send PING to all current agents
        current_agents = list(self.agent_connections.items())
        self._pending_pongs.clear()
        for seat_id, ws in current_agents:
            try:
                await ws.send_json(ws_envelope(Msg.PING, {}))
                self._pending_pongs.add(seat_id)
            except Exception:
                self.agent_connections.pop(seat_id, None)

    async def close_all(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close agent connections
        for seat_id in list(self.agent_connections):
            ws = self.agent_connections.pop(seat_id)
            try:
                await ws.close(code=1001, reason="server shutting down")
            except Exception:  # noqa: S110
                pass  # Best-effort cleanup on shutdown

        # Close dashboard connections
        for ws in list(self.dashboard_connections):
            try:
                await ws.close(code=1001, reason="server shutting down")
            except Exception:  # noqa: S110
                pass  # Best-effort cleanup on shutdown
        self.dashboard_connections.clear()


# ---------------------------------------------------------------------------
# Module-level singleton — the production fast path
# ---------------------------------------------------------------------------

manager = WebSocketManager()
"""Global WebSocketManager instance for the application.

Use this in routers, services, and the FastAPI lifespan.  Unit tests
that need isolated state should construct :class:`WebSocketManager`
directly.
"""
