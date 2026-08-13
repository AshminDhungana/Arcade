"""Section C regressions: C.8 agent crash recovery + C.4 pause sync.

C.8: a disconnected agent (crash) reconnects and REGISTERs mid-session —
the seat must stay IN_USE (not be clobbered to ONLINE/AVAILABLE), SYNC
reconciles the elapsed time, and checkout bills the adopted elapsed exactly
once.
C.4: pause/resume exclude the paused window from billable elapsed time and
push SHOW_OVERLAY/HIDE_OVERLAY envelopes to the agent with PAUSED → IN_USE
dashboard broadcasts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from .utils import auth_headers


@pytest.fixture
def ws_db(integration_db):
    """Route ws_manager's internal ``AsyncSessionLocal`` to the fixture DB.

    ``connect_agent``/``disconnect_agent``/``_handle_register``/
    ``_handle_sync`` import ``AsyncSessionLocal`` from
    ``backend.core.database`` at call time, so patching it there routes every
    ws_manager DB touch at the in-memory integration database.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(integration_db.bind, expire_on_commit=False)

    class _SessionCM:
        def __init__(self):
            self.session = None

        async def __aenter__(self):
            self.session = session_factory()
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            await self.session.close()
            return False

    def _local_factory():
        return _SessionCM()

    with patch("backend.core.database.AsyncSessionLocal", _local_factory):
        yield


async def _connect_agent(ws_manager, seat_id: str, mock_ws) -> None:
    """Connect an agent using the real secret-check path, no real socket."""
    mock_ws.accept = AsyncMock()
    mock_ws.close = AsyncMock()
    with patch.object(ws_manager, "_start_heartbeat", new=AsyncMock()):
        success = await ws_manager.connect_agent(seat_id, "test-secret", mock_ws)
    assert success is True


async def test_c8_agent_crash_recovery_bills_adopted_elapsed_once(
    integration_client,
    integration_db,
    seeded_zone,
    seeded_seat,
    admin_staff,
    ws_db,
):
    """Agent crashes mid-session; reconnect keeps IN_USE; SYNC adopts ALE;
    checkout bills the adopted elapsed and creates exactly one invoice."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus
    from backend.repositories import seat_repo, session_repo

    await seat_repo.set_agent_secret(integration_db, seeded_seat.id, "test-secret")
    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    # 1. Start session via the API (house contract: 201 + id)
    resp = await integration_client.post(
        "/api/sessions",
        json={"seat_id": seeded_seat.id},
        headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
    )
    assert resp.status_code == 201, resp.text
    session_id = resp.json()["id"]

    await integration_db.refresh(seeded_seat)
    assert seeded_seat.status == SeatStatus.IN_USE

    # 2. Agent connects, then crashes (disconnect) → seat OFFLINE
    mock_ws = AsyncMock()
    await _connect_agent(ws_manager, seeded_seat.id, mock_ws)
    await ws_manager.disconnect_agent(seeded_seat.id)

    await integration_db.refresh(seeded_seat)
    assert seeded_seat.status == SeatStatus.OFFLINE

    # 3. Agent restarts and REGISTERs mid-session → seat must stay IN_USE
    mock_ws2 = AsyncMock()
    await _connect_agent(ws_manager, seeded_seat.id, mock_ws2)
    await ws_manager.handle_agent_message(
        seeded_seat.id,
        {
            "type": "REGISTER",
            "payload": {"mac_address": "aa:bb:cc:dd:ee:ff", "hostname": "crash-pc"},
        },
    )

    await integration_db.refresh(seeded_seat)
    assert seeded_seat.status == SeatStatus.IN_USE

    # 4. Backdate the session; agent SYNCs with a local elapsed far above SAE
    session = await session_repo.get_by_id(integration_db, session_id)
    session.started_at = datetime.now(UTC) - timedelta(minutes=5)
    session.total_paused_seconds = 0
    await integration_db.commit()

    response = await ws_manager.handle_agent_message(
        seeded_seat.id,
        {
            "type": "SYNC",
            "payload": {"session_id": session_id, "local_elapsed_seconds": 800.0},
        },
    )
    assert response["type"] == "SYNC_ACK"
    assert response["action"] == "ADOPT_ALE"
    assert response["chosen_elapsed_seconds"] == 800.0

    # Refresh the shared fixture session so checkout reads the adopted anchor
    await integration_db.refresh(session)

    # 5. Checkout bills the adopted elapsed exactly once (no double billing)
    checkout_resp = await integration_client.post(
        f"/api/sessions/{session_id}/checkout",
        json={"payment_method": "CASH"},
        headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
    )
    assert checkout_resp.status_code == 201, checkout_resp.text
    invoice = checkout_resp.json()
    # 800 s at PER_MINUTE 100 paise/min → ceil(800/60)=14 min → 1400 paise
    assert invoice["time_charge_paise"] == 1400

    async with integration_db.bind.connect() as conn:
        count = (
            await conn.execute(
                text("SELECT COUNT(*) FROM invoices WHERE session_id = :sid"),
                {"sid": session_id},
            )
        ).scalar_one()
    assert count == 1


async def test_c4_pause_excludes_elapsed_and_syncs_agent(
    integration_client,
    integration_db,
    seeded_zone,
    seeded_seat,
    admin_staff,
    ws_db,
):
    """Pause stops the clock; resume bills only the active window and the
    agent receives SHOW_OVERLAY/HIDE_OVERLAY with PAUSED → IN_USE broadcasts."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus
    from backend.repositories import seat_repo, session_repo
    from backend.services.billing_service import _compute_elapsed_seconds

    await seat_repo.set_agent_secret(integration_db, seeded_seat.id, "test-secret")
    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    # Agent connected so pause/resume envelopes reach it
    mock_ws = AsyncMock()
    await _connect_agent(ws_manager, seeded_seat.id, mock_ws)

    resp = await integration_client.post(
        "/api/sessions",
        json={"seat_id": seeded_seat.id},
        headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
    )
    assert resp.status_code == 201, resp.text
    session_id = resp.json()["id"]

    session = await session_repo.get_by_id(integration_db, session_id)
    session.started_at = datetime.now(UTC) - timedelta(minutes=5)
    session.total_paused_seconds = 0
    await integration_db.commit()

    # Capture dashboard broadcasts to assert PAUSED → IN_USE
    broadcasts: list[dict] = []
    original_broadcast = ws_manager.broadcast_to_dashboards

    async def capture_broadcast(event, payload):
        broadcasts.append({"event": event, "payload": payload})
        return await original_broadcast(event, payload)

    mock_ws.send_json.reset_mock()
    with patch.object(ws_manager, "broadcast_to_dashboards", capture_broadcast):
        # Pause with a known 120 s pause window
        pause_resp = await integration_client.patch(
            f"/api/sessions/{session_id}/pause",
            headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
        )
        assert pause_resp.status_code == 200, pause_resp.text

        session = await session_repo.get_by_id(integration_db, session_id)
        session.paused_at = datetime.now(UTC) - timedelta(seconds=120)
        await integration_db.commit()

        resume_resp = await integration_client.patch(
            f"/api/sessions/{session_id}/resume",
            headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
        )
        assert resume_resp.status_code == 200, resume_resp.text

    # Paused window was accrued exactly
    session = await session_repo.get_by_id(integration_db, session_id)
    assert session.total_paused_seconds == 120

    # Billable elapsed excludes the paused window (300 s - 120 s ≈ 180 s)
    elapsed = _compute_elapsed_seconds(session)
    assert 178 <= elapsed <= 182

    # Agent received both envelopes (payload shape ignored beyond type)
    sent_types = [c.args[0]["type"] for c in mock_ws.send_json.call_args_list]
    assert "SHOW_OVERLAY" in sent_types
    assert "HIDE_OVERLAY" in sent_types

    # Dashboard broadcasts carried PAUSED → IN_USE for the seat
    seat_broadcasts = [
        b["payload"]["status"]
        for b in broadcasts
        if b["event"] == "seat_updated" and b["payload"].get("id") == seeded_seat.id
    ]
    assert "PAUSED" in seat_broadcasts
    assert "IN_USE" in seat_broadcasts
