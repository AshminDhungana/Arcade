# backend/tests/test_session_schema_6_5_4.py
from backend.schemas.seat import SeatResponse
from backend.schemas.session import SessionResponse


def test_session_response_has_assigned_end_at():
    s = SessionResponse(
        id="s1",
        seat_id="seat1",
        member_id=None,
        shift_id=None,
        status="ACTIVE",
        started_at="2026-07-17T10:00:00+00:00",
        total_paused_seconds=0,
        locked_rate_paise=0,
        locked_pricing_model="PER_MINUTE",
        package_entitlement_id=None,
        promotion_id=None,
        discount_paise=0,
        payment_method=None,
        created_at="2026-07-17T10:00:00+00:00",
        updated_at="2026-07-17T10:00:00+00:00",
    )
    assert s.assigned_end_at is None


def test_seat_response_has_assigned_end_at():
    seat = SeatResponse(
        id="seat1",
        name="PC-01",
        zone_id="z1",
        status="IN_USE",
        is_console=False,
        overlay_forced=False,
        wol_attempts=0,
        wol_successes=0,
        wol_failures=0,
        created_at="2026-07-17T10:00:00+00:00",
        updated_at="2026-07-17T10:00:00+00:00",
    )
    assert seat.assigned_end_at is None
