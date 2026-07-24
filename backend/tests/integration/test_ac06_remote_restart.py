"""AC-06: Remote restart/shutdown command delivered to agent over WebSocket."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketState


async def test_remote_restart_delivered_over_ws(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Remote restart command is delivered to the agent's WebSocket connection."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus
    from backend.services import remote_command_service

    # Set up seat with agent connection simulated
    seeded_seat.status = SeatStatus.IN_USE
    seeded_seat.mac_address = "aa:bb:cc:dd:ee:ff"
    await integration_db.commit()

    # Mock agent connection by directly adding to connections dict
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.send_json = AsyncMock()
    ws_manager.agent_connections[seeded_seat.id] = mock_ws

    # Capture sent messages
    sent_messages = []
    original_send = ws_manager.send_to_agent

    async def capture_send(seat_id, message):
        sent_messages.append({"seat_id": seat_id, "message": message})
        return await original_send(seat_id, message)

    with patch.object(ws_manager, "send_to_agent", capture_send):
        # Call remote restart (function is restart_seat, not restart_pc)
        await remote_command_service.restart_seat(
            integration_db, seeded_seat.id, admin_staff
        )

        # Verify command was sent
        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert msg["seat_id"] == seeded_seat.id
        assert msg["message"]["type"] == "RESTART"
        assert "delay_seconds" in msg["message"]["payload"]


async def test_remote_shutdown_delivered_over_ws(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Remote shutdown command is delivered to the agent's WebSocket connection."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus
    from backend.services import remote_command_service

    seeded_seat.status = SeatStatus.IN_USE
    await integration_db.commit()

    # Mock agent connection
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.send_json = AsyncMock()
    ws_manager.agent_connections[seeded_seat.id] = mock_ws

    sent_messages = []
    original_send = ws_manager.send_to_agent

    async def capture_send(seat_id, message):
        sent_messages.append({"seat_id": seat_id, "message": message})
        return await original_send(seat_id, message)

    with patch.object(ws_manager, "send_to_agent", capture_send):
        await remote_command_service.shutdown_seat(
            integration_db, seeded_seat.id, admin_staff
        )

        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert msg["seat_id"] == seeded_seat.id
        assert msg["message"]["type"] == "SHUTDOWN"
        assert "delay_seconds" in msg["message"]["payload"]


async def test_remote_restart_fails_when_agent_offline(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Remote restart returns error when agent is offline."""
    from backend.models import SeatStatus
    from backend.services import remote_command_service
    from backend.services.remote_command_service import AgentOfflineHttpError

    seeded_seat.status = SeatStatus.IN_USE
    await integration_db.commit()

    # Don't connect agent - it's offline (agent_connections dict is empty)
    with pytest.raises(AgentOfflineHttpError):
        await remote_command_service.restart_seat(
            integration_db, seeded_seat.id, admin_staff
        )
