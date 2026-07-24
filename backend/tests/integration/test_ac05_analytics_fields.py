"""AC-05: Analytics /summary endpoint returns all required fields."""

from datetime import UTC, datetime, timedelta

from .utils import auth_headers, seed_minimal_analytics_data


async def test_analytics_summary_fields(integration_client, integration_db):
    """Analytics summary contains all required fields per schema."""
    from backend.models import SeatStatus

    # Seed minimal data
    await seed_minimal_analytics_data(integration_db)

    # Create some sessions for analytics
    from backend.models import MemberTier, PricingModel, Zone
    from backend.repositories import member_repo, zone_repo
    from backend.repositories import seat_repo as seat_repo_module

    zone = await zone_repo.get_by_name(integration_db, "Test Zone")
    if not zone:
        zone = Zone(
            name="Test Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        integration_db.add(zone)
        await integration_db.flush()

    seat1 = await seat_repo_module.create(integration_db, name="PC-01", zone_id=zone.id)
    seat1.status = SeatStatus.AVAILABLE
    seat2 = await seat_repo_module.create(integration_db, name="PC-02", zone_id=zone.id)
    seat2.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    member = await member_repo.create(
        integration_db, name="Test Member", phone="9999999999"
    )
    member.tier = MemberTier.BRONZE
    await integration_db.commit()

    from backend.models import PaymentMethod, Staff, StaffRole
    from backend.services import billing_service, session_service

    admin = Staff(
        id="admin-id",
        name="Admin",
        pin_hash="argon2id",
        role=StaffRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    integration_db.add(admin)
    await integration_db.commit()

    # Start and checkout a few sessions
    for i in range(3):
        seat = seat1 if i % 2 == 0 else seat2
        session = await session_service.start_session(
            integration_db, seat.id, member.id, admin
        )
        # Simulate elapsed time
        from backend.repositories import session_repo as sess_repo

        db_session = await sess_repo.get_by_id(integration_db, session.id)
        start_offset = 30 + i * 15  # 30, 45, 60 minutes
        db_session.started_at = datetime.now(UTC) - timedelta(minutes=start_offset)
        await integration_db.commit()

        await billing_service.checkout_session(
            integration_db, session.id, PaymentMethod.CASH, admin
        )
        await integration_db.commit()

    # Call analytics summary

    resp = await integration_client.get(
        "/api/analytics/summary", headers=auth_headers(staff_id=admin.id, role="ADMIN")
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Required fields per AnalyticsSummary schema
    assert "total_revenue_paise" in data
    assert "session_count" in data
    assert "average_duration_seconds" in data
    assert "busiest_hour" in data
    assert "weekly_revenue" in data
    assert "top_pos_items" in data
    assert "member_registration_trend" in data
    assert "zone_utilisation" in data
    assert "member_stats" in data
    assert "health_alerts" in data
    assert "upcoming_reservations" in data
    assert "wol_success_rates" in data
    assert "current_shift_id" in data
    assert "shift_opened_at" in data

    # Type checks
    assert isinstance(data["total_revenue_paise"], int)
    assert isinstance(data["session_count"], int)
    assert isinstance(data["average_duration_seconds"], (int, float))
    assert isinstance(data["busiest_hour"], (dict, type(None)))
    assert isinstance(data["weekly_revenue"], list)
    assert isinstance(data["top_pos_items"], list)
    assert isinstance(data["member_registration_trend"], list)
    assert isinstance(data["zone_utilisation"], list)
    assert isinstance(data["member_stats"], dict)
    assert isinstance(data["health_alerts"], list)
    assert isinstance(data["upcoming_reservations"], list)
    assert isinstance(data["wol_success_rates"], list)

    # Value sanity checks
    assert data["session_count"] == 3
    assert data["total_revenue_paise"] > 0
    assert data["average_duration_seconds"] >= 30 * 60  # 30 minutes in seconds


async def test_analytics_summary_empty(integration_client, integration_db):
    """Analytics summary handles empty data gracefully."""
    from backend.models import Staff, StaffRole

    admin = Staff(
        id="admin-id",
        name="Admin",
        pin_hash="argon2id",
        role=StaffRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    integration_db.add(admin)
    await integration_db.commit()

    resp = await integration_client.get(
        "/api/analytics/summary", headers=auth_headers(staff_id=admin.id, role="ADMIN")
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["session_count"] == 0
    assert data["total_revenue_paise"] == 0
    assert data["average_duration_seconds"] == 0
    assert data["busiest_hour"] is None
    # weekly_revenue returns 7-day list with zeros for empty data
    assert isinstance(data["weekly_revenue"], list)
    assert len(data["weekly_revenue"]) == 7
    assert all(d["total_paise"] == 0 for d in data["weekly_revenue"])
    assert data["top_pos_items"] == []
    # member_registration_trend returns 30-day list with zeros for empty data
    assert isinstance(data["member_registration_trend"], list)
    assert len(data["member_registration_trend"]) == 30
    assert all(d["count"] == 0 for d in data["member_registration_trend"])
    assert data["zone_utilisation"] == []
    assert data["member_stats"]["new_today"] == 0
    assert data["member_stats"]["active_last_30d"] == 0
    assert data["health_alerts"] == []
    assert data["upcoming_reservations"] == []
    assert data["wol_success_rates"] == []
    assert data["current_shift_id"] is None
    assert data["shift_opened_at"] is None
