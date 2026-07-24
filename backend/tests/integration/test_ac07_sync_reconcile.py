"""AC-07: SYNC reconciliation logic — server reconciles elapsed time correctly."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch


async def test_sync_reconcile_accepts_sae_within_tolerance(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """SYNC: when agent elapsed is within 5s tolerance, server accepts SAE."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus
    from backend.repositories import session_repo
    from backend.services import session_service

    # Seed: active session started 10 minutes ago
    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session_resp = await session_service.start_session(
        integration_db, seeded_seat.id, admin_staff.id, admin_staff
    )
    # Get the actual ORM object to modify
    session = await session_repo.get_by_id(integration_db, session_resp.id)
    # Ensure timezone-aware datetime
    session.started_at = datetime.now(UTC) - timedelta(minutes=10)
    session.started_at = session.started_at.replace(tzinfo=UTC)
    session.total_paused_seconds = 0
    await integration_db.commit()

    # Wait a tiny bit then compute SAE to make test deterministic
    import asyncio

    await asyncio.sleep(0.01)
    now = datetime.now(UTC)
    sae_expected = (now - session.started_at).total_seconds()

    # Patch session_repo.get_by_id to use the test session
    original_get_by_id = session_repo.get_by_id

    async def mock_get_by_id(db, session_id):
        return await original_get_by_id(integration_db, session_id)

    # Agent sends SYNC with local_elapsed close to SAE (within 5s tolerance)
    agent_elapsed = sae_expected + 1.0  # 1 second drift, well within 5s tolerance
    with patch.object(session_repo, "get_by_id", mock_get_by_id):
        response = await ws_manager.handle_agent_message(
            seeded_seat.id,
            {
                "type": "SYNC",
                "payload": {
                    "session_id": session.id,
                    "local_elapsed_seconds": agent_elapsed,
                },
            },
        )

    assert response["type"] == "SYNC_ACK"
    assert response["action"] == "ACCEPT_SAE"
    assert abs(response["chosen_elapsed_seconds"] - sae_expected) < 5.0


async def test_sync_reconcile_adopts_ale_when_drift_exceeds_tolerance(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """SYNC: when drift > 5s, server adopts agent's local elapsed (ADOPT_ALE)."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus
    from backend.repositories import session_repo
    from backend.services import session_service

    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session = await session_service.start_session(
        integration_db, seeded_seat.id, admin_staff.id, admin_staff
    )
    # Ensure timezone-aware datetime
    session.started_at = datetime.now(UTC) - timedelta(minutes=10)
    session.started_at = session.started_at.replace(tzinfo=UTC)
    session.total_paused_seconds = 0
    await integration_db.commit()

    # Patch session_repo.get_by_id to use the test session
    original_get_by_id = session_repo.get_by_id

    async def mock_get_by_id(db, session_id):
        return await original_get_by_id(integration_db, session_id)

    # Agent elapsed = 800s, SAE = 600s → drift = 200s > 5s tolerance
    agent_elapsed = 800.0
    with patch.object(session_repo, "get_by_id", mock_get_by_id):
        response = await ws_manager.handle_agent_message(
            seeded_seat.id,
            {
                "type": "SYNC",
                "payload": {
                    "session_id": session.id,
                    "local_elapsed_seconds": agent_elapsed,
                },
            },
        )

    assert response["type"] == "SYNC_ACK"
    assert response["action"] == "ADOPT_ALE"
    assert response["chosen_elapsed_seconds"] == 800.0


async def test_sync_reconcile_missing_session_returns_error(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """SYNC: missing session_id returns error in payload."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus

    seeded_seat.status = SeatStatus.IN_USE
    await integration_db.commit()

    response = await ws_manager.handle_agent_message(
        seeded_seat.id, {"type": "SYNC", "payload": {"local_elapsed_seconds": 100}}
    )

    assert response["type"] == "SYNC_ACK"
    assert response["error"] == "Missing session_id in SYNC payload"
    assert response["session_id"] is None


async def test_sync_reconcile_nonexistent_session_falls_back_to_ale(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """SYNC: nonexistent session_id falls back to agent elapsed."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus

    seeded_seat.status = SeatStatus.IN_USE
    await integration_db.commit()

    response = await ws_manager.handle_agent_message(
        seeded_seat.id,
        {
            "type": "SYNC",
            "payload": {"session_id": "nonexistent-id", "local_elapsed_seconds": 500},
        },
    )

    assert response["type"] == "SYNC_ACK"
    assert response["action"] == "NO_SESSION"
    assert response["chosen_elapsed_seconds"] == 500.0


async def test_sync_broadcasts_synced_status_to_dashboards(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """SYNC: broadcasts SEAT_UPDATED with synced state to dashboards."""
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus
    from backend.services import session_service

    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session = await session_service.start_session(
        integration_db, seeded_seat.id, admin_staff.id, admin_staff
    )
    session.started_at = datetime.now(UTC) - timedelta(minutes=10)
    session.total_paused_seconds = 0
    await integration_db.commit()

    # Capture broadcast
    broadcasts = []
    original_broadcast = ws_manager.broadcast_to_dashboards

    async def capture_broadcast(event, payload):
        broadcasts.append({"event": event, "payload": payload})
        return await original_broadcast(event, payload)

    with patch.object(ws_manager, "broadcast_to_dashboards", capture_broadcast):
        await ws_manager.handle_agent_message(
            seeded_seat.id,
            {
                "type": "SYNC",
                "payload": {"session_id": session.id, "local_elapsed_seconds": 600},
            },
        )

    assert len(broadcasts) > 0
    broadcast = broadcasts[-1]
    assert broadcast["event"] == "seat_updated"
    assert broadcast["payload"]["status"] == "SYNCED"
    assert "chosen_elapsed_seconds" in broadcast["payload"]
    assert "drift" in broadcast["payload"]
    assert "action" in broadcast["payload"]
