"""AC-01: WebSocket seat status broadcasts within 1 second."""

import asyncio
from unittest.mock import patch

from .utils import TimingCapture, wait_for_condition


async def test_ws_seat_status_broadcast_latency(
    integration_client, integration_db, seeded_seat, mock_staff
):
    """Seat status change broadcasts to dashboards within 1 second."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.services import seat_service

    timing = TimingCapture()
    captured_broadcasts = []

    # Patch broadcast to capture timing
    original_broadcast = ws_manager.broadcast_to_dashboards

    async def capturing_broadcast(event, data):
        timing.mark("broadcast_received")
        captured_broadcasts.append((event, data))
        return await original_broadcast(event, data)

    with patch.object(ws_manager, "broadcast_to_dashboards", capturing_broadcast):
        timing.mark("service_call_start")
        await seat_service.set_maintenance(
            integration_db, seeded_seat.id, "Test maintenance", mock_staff
        )
        timing.mark("service_call_end")

        # Wait for broadcast (near-instant in mocked env)
        await wait_for_condition(
            lambda: asyncio.sleep(0, result=len(captured_broadcasts) > 0)
        )
        timing.mark("broadcast_received")

    latency_ms = timing.elapsed_ms("service_call_start", "broadcast_received")
    assert latency_ms < 1000, f"Broadcast latency {latency_ms:.1f}ms exceeds 1000ms"
    assert any(
        e == "seat_updated" and d["id"] == seeded_seat.id
        for e, d in captured_broadcasts
    )
