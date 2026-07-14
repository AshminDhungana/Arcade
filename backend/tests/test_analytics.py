# backend/tests/test_analytics.py  (head of file — fixtures + this test)
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
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
