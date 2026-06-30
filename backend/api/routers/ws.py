"""FastAPI WebSocket endpoints for Arcade.

- ``GET /ws/dashboard`` — Dashboard real-time feed.
- ``GET /ws/agent/{seat_id}`` — Per-seat agent command channel.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.core.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket) -> None:
    """Accept a dashboard client and keep the socket alive for broadcasts.

    Dashboards are primarily listeners. They receive ``seat_updated``,
    ``health_update``, ``announcement``, and ``alert`` events.
    """
    await manager.connect_dashboard(websocket)
    try:
        while True:
            # Dashboards may send messages (e.g., heartbeat, ping)
            data = await websocket.receive_json()
            msg_type = data.get("type", "").upper()
            if msg_type == "PONG":
                # Dashboards sending PONG is harmless, no-op
                pass
            else:
                # Future: handle dashboard-initiated messages (if any)
                pass
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect_dashboard(websocket)


@router.websocket("/ws/agent/{seat_id}")
async def agent_websocket(
    websocket: WebSocket,
    seat_id: str,
    secret: str = Query(...),  # noqa: B008
) -> None:
    """Accept an agent connection for the given seat_id.

    The ``secret`` query parameter is validated against ``agent_secrets``
    from the config. If the secret is invalid the connection is closed
    immediately with code 1008.

    After successful connection, the agent sends messages (REGISTER, HEALTH,
    SYNC, STAFF_OVERRIDE) and the server dispatches them via
    :meth:`WebSocketManager.handle_agent_message`.
    """
    connected = await manager.connect_agent(seat_id, secret, websocket)
    if not connected:
        return

    try:
        while True:
            message = await websocket.receive_json()
            await manager.handle_agent_message(seat_id, message)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect_agent(seat_id)
