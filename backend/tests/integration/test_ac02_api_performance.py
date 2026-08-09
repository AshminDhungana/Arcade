"""AC-02: Session start < 2s, Checkout < 10s."""

import time
from datetime import UTC, datetime, timedelta

from .utils import auth_headers


async def test_session_start_response_time(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """POST /api/sessions responds within 2 seconds."""
    from backend.models import SeatStatus

    # Re-seed seat to available
    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    start = time.perf_counter()
    resp = await integration_client.post(
        "/api/sessions",
        json={"seat_id": seeded_seat.id},
        headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
    )
    elapsed = time.perf_counter() - start
    assert resp.status_code == 201
    assert elapsed < 2.0, f"Session start took {elapsed:.2f}s, expected < 2s"


async def test_checkout_response_time(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """POST /api/sessions/{id}/checkout responds within 10 seconds."""
    from backend.models import SeatStatus

    # Re-seed seat to available
    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    resp = await integration_client.post(
        "/api/sessions",
        json={"seat_id": seeded_seat.id},
        headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
    )
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Simulate 30 min elapsed with timezone-aware datetime
    from backend.repositories import session_repo

    session = await session_repo.get_by_id(integration_db, session_id)
    session.started_at = datetime.now(UTC) - timedelta(minutes=30)
    await integration_db.commit()

    start = time.perf_counter()
    resp = await integration_client.post(
        f"/api/sessions/{session_id}/checkout",
        json={"payment_method": "CASH"},
        headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
    )
    elapsed = time.perf_counter() - start

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["total_paise"] >= 0
    assert "created_at" in data
    assert elapsed < 10.0, f"Checkout took {elapsed:.2f}s, expected < 10s"


async def test_analytics_summary_performance(integration_client, admin_staff):
    """GET /api/analytics/summary completes in < 2 seconds on seeded dataset."""
    start = time.perf_counter()
    resp = await integration_client.get(
        "/api/analytics/summary",
        headers=auth_headers(staff_id=admin_staff.id, role="ADMIN"),
    )
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200
    data = resp.json()
    # Verify key fields present
    assert "total_revenue_paise" in data
    assert "session_count" in data
    assert "average_duration_seconds" in data
    assert elapsed < 2.0, f"Analytics query took {elapsed:.2f}s, expected < 2s"
