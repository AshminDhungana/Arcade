# backend/tests/test_analytics.py  (head of file — fixtures + this test)
from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.ws_manager import manager as _ws_manager
from backend.main import app
from backend.models import (
    GamingSession,
    Invoice,
    Member,
    MenuItem,
    Reservation,
    Seat,
    SessionPOSItem,
    Zone,
)
from backend.models._enums import (
    MemberTier,
    PaymentMethod,
    ReservationStatus,
    SeatStatus,
    SessionStatus,
    StaffRole,
)
from backend.scripts import seed_perf
from backend.services import analytics_service


def _mock(role: StaffRole) -> object:
    class _S:
        id = "mock-staff-id"
        name = "Mock"
        is_active = True
        token_version = 0

    s = _S()
    s.role = role
    return s


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock(StaffRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def cashier_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def _seed_small(db: AsyncSession, now: datetime) -> dict:
    """Insert a deterministic, small dataset anchored to *now*."""
    zone = Zone(
        name="Z",
        rate_per_minute_paise=20,
        rate_per_hour_paise=1200,
        pricing_model="PER_MINUTE",
        block_minutes=15,
    )
    db.add(zone)
    await db.flush()
    seat = Seat(name="Seat 001", zone_id=zone.id, status=SeatStatus.AVAILABLE.value)
    db.add(seat)
    await db.flush()
    menu = MenuItem(
        name="Tea", category="Beverages", price_paise=2500, is_available=True
    )
    db.add(menu)
    await db.flush()
    member = Member(
        name="Alice",
        phone="+9779800000999",
        tier=MemberTier.BRONZE.value,
        created_at=now.replace(hour=9, minute=0, second=0, microsecond=0),
    )
    db.add(member)
    await db.flush()

    started = now.replace(hour=10, minute=0, second=0, microsecond=0)
    ended = started + timedelta(minutes=60)
    sess = GamingSession(
        seat_id=seat.id,
        member_id=member.id,
        status=SessionStatus.COMPLETED,
        started_at=started,
        ended_at=ended,
        total_paused_seconds=0,
        locked_rate_paise=20,
        locked_pricing_model="PER_MINUTE",
        payment_method=PaymentMethod.CASH,
    )
    db.add(sess)
    await db.flush()
    db.add(
        Invoice(
            session_id=sess.id,
            member_id=member.id,
            total_paise=5000,
            payment_method=PaymentMethod.CASH,
            created_at=ended,
        )
    )
    db.add(
        SessionPOSItem(
            session_id=sess.id,
            menu_item_id=menu.id,
            quantity=3,
            unit_price_paise=menu.price_paise,
        )
    )
    res = Reservation(
        seat_id=seat.id,
        customer_name="Bob",
        reserved_from=now + timedelta(hours=2),
        reserved_until=now + timedelta(hours=3),
        status=ReservationStatus.CONFIRMED.value,
        created_by_staff_id="seed",
    )
    db.add(res)
    seat.wol_attempts = 10
    seat.wol_successes = 8
    await db.flush()
    return {"seat_id": seat.id, "reservation_id": res.id}


async def test_summary_revenue_and_counts(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await _seed_small(db, now)
    summary = await analytics_service.get_summary(db)
    assert summary.total_revenue_paise == 5000
    assert summary.session_count >= 1
    assert summary.average_duration_seconds == pytest.approx(3600.0)
    assert len(summary.weekly_revenue) == 7
    assert any(d.total_paise == 5000 for d in summary.weekly_revenue)
    assert summary.busiest_hour is not None
    assert summary.busiest_hour.session_count >= 1


async def test_summary_items_zone_members_wol(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await _seed_small(db, now)
    summary = await analytics_service.get_summary(db)
    assert summary.top_pos_items and summary.top_pos_items[0].name == "Tea"
    assert summary.zone_utilisation and summary.zone_utilisation[0].zone_name == "Z"
    assert summary.member_stats.new_today >= 1
    assert summary.member_stats.active_last_30d >= 1
    assert summary.wol_success_rates and summary.wol_success_rates[0].rate_pct == 80.0
    assert summary.upcoming_reservations
    assert summary.upcoming_reservations[0].customer_name == "Bob"


def test_compute_health_alerts_pure() -> None:
    seat = Seat(name="S1", zone_id="z", status=SeatStatus.AVAILABLE.value)
    seat.id = "s1"  # not flushed to DB here; give a stable id for lookup
    now = datetime.now(UTC)
    alerts = analytics_service.compute_health_alerts(
        [seat],
        health_data={seat.id: {"cpu_temp": 90.0}},
        received_at={},
        now=now,
    )
    assert len(alerts) == 1
    assert set(alerts[0].reasons) == {"cpu_temp_red", "no_health_report"}

    # Maintenance seats are excluded even with no report.
    mseat = Seat(name="M", zone_id="z", status=SeatStatus.MAINTENANCE.value)
    assert analytics_service.compute_health_alerts([mseat], {}, {}, now) == []


async def test_summary_endpoint_admin(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    now = datetime.now(UTC)
    await _seed_small(db, now)
    resp = await admin_client.get("/api/analytics/summary")
    assert resp.status_code == 200
    assert resp.json()["total_revenue_paise"] == 5000


async def test_summary_endpoint_forbidden_for_cashier(
    cashier_client: AsyncClient,
) -> None:
    resp = await cashier_client.get("/api/analytics/summary")
    assert resp.status_code == 403


async def test_summary_under_two_seconds_on_year(db: AsyncSession) -> None:
    await seed_perf.seed_structural(db)
    await seed_perf.seed_year(db)
    await db.commit()
    start = time.perf_counter()
    summary = await analytics_service.get_summary(db)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"summary took {elapsed:.2f}s"
    assert summary is not None


async def test_summary_member_registration_trend_fills_gaps(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    for i, offset in enumerate([0, 0, 3]):
        db.add(
            Member(
                name=f"M{i}",
                phone=f"+977980000{i:04d}",
                created_at=(now - timedelta(days=offset)).replace(
                    hour=9, minute=0, second=0, microsecond=0
                ),
            )
        )
    await db.commit()

    summary = await analytics_service.get_summary(db)
    trend = summary.member_registration_trend
    assert len(trend) == 30
    today_key = now.strftime("%Y-%m-%d")
    three_days_key = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    ten_days_key = (now - timedelta(days=10)).strftime("%Y-%m-%d")
    assert next(d.count for d in trend if d.date == today_key) == 2
    assert next(d.count for d in trend if d.date == three_days_key) == 1
    assert next(d.count for d in trend if d.date == ten_days_key) == 0


@pytest_asyncio.fixture
async def clean_health() -> AsyncGenerator[None]:
    """Isolate the module-level WebSocketManager health state so the
    summary's health_alerts assertion is deterministic (no real agents)."""
    _ws_manager._health_data.clear()
    _ws_manager._health_received_at.clear()
    yield
    _ws_manager._health_data.clear()
    _ws_manager._health_received_at.clear()


async def test_summary_all_fields_on_30day_dataset(
    db: AsyncSession, clean_health: None
) -> None:
    """Every AnalyticsSummary field has an exact, deterministic value on the
    30-day seed (Task1)."""
    await seed_perf.seed_30_day(db)
    await db.commit()
    s = await analytics_service.get_summary(db)

    # Today-only window
    assert s.total_revenue_paise == 8000
    assert s.session_count == 2
    assert s.average_duration_seconds == pytest.approx(2700.0)

    # Busiest hour (30-day window): hour 10 has S1 + S3 = 2 sessions
    assert s.busiest_hour is not None
    assert s.busiest_hour.hour == 10
    assert s.busiest_hour.session_count == 2

    # Weekly revenue: 7 days, only today has revenue (8000)
    assert len(s.weekly_revenue) == 7
    assert sum(d.total_paise for d in s.weekly_revenue) == 8000

    # Top POS items: Tea = 2 (S1) + 3 (S2) = 5
    assert s.top_pos_items and s.top_pos_items[0].name == "Tea"
    assert s.top_pos_items[0].quantity == 5

    # Member registration trend: 30 entries, 1 new 29d-ago, 1 new today
    assert len(s.member_registration_trend) == 30
    assert s.member_registration_trend[0].count == 1
    assert s.member_registration_trend[-1].count == 1
    assert sum(d.count for d in s.member_registration_trend) == 2

    # Zone utilisation (7-day window): 1.5 session-hrs over 1 seat.
    # available_hours = 7d window but measured up to `now`, so it is
    # 168 + (hours into today); assert the deterministic parts exactly.
    assert s.zone_utilisation and s.zone_utilisation[0].zone_name == "Z"
    assert s.zone_utilisation[0].session_hours == pytest.approx(1.5)
    assert s.zone_utilisation[0].available_hours >= 168.0
    assert s.zone_utilisation[0].available_hours < 192.0

    # Member stats
    assert s.member_stats.new_today == 1
    assert s.member_stats.active_last_30d == 1
    assert (
        s.member_stats.top_spenders and s.member_stats.top_spenders[0].name == "Alice"
    )

    # WoL: 8 successes / 10 attempts = 80.0%
    assert s.wol_success_rates and s.wol_success_rates[0].rate_pct == pytest.approx(
        80.0
    )

    # Upcoming reservation (today)
    assert s.upcoming_reservations and s.upcoming_reservations[0].customer_name == "Bob"

    # No health reports -> no alerts
    assert s.health_alerts == []

    # No open shift
    assert s.current_shift_id is None
    assert s.shift_opened_at is None
