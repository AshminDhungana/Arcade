"""Tests for sweep_expired_sessions (Task 7 / Epic 6.5.4)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import GamingSession, SeatStatus, SessionStatus
from backend.repositories import seat_repo, session_repo
from backend.services.session_service import sweep_expired_sessions

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on an in-memory SQLite DB."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def zone_and_seat(db: AsyncSession):
    """Create a zone and seat; return (zone, seat)."""
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()

    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    return zone, seat


def _make_session(seat, now, end):
    return GamingSession(
        seat_id=seat.id,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model="PER_MINUTE",
        status=SessionStatus.ACTIVE,
        assigned_end_at=end,
    )


async def test_expired_session_forces_overlay_and_expired(db, zone_and_seat):
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    s = _make_session(seat, now, now - timedelta(minutes=1))  # already past
    db.add(s)
    await db.commit()
    await db.refresh(s)
    with (
        patch("backend.services.session_service.remote_command_service") as rc,
        patch("backend.services.session_service.ws_manager") as ws,
    ):
        rc.force_overlay = AsyncMock()
        ws.send_to_agent = AsyncMock()
        ws.broadcast_to_dashboards = AsyncMock()
        await sweep_expired_sessions(db)
    rc.force_overlay.assert_awaited_once_with(db, seat.id, True, None)
    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.EXPIRED


async def test_warning_sent_once_in_window(db, zone_and_seat):
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    s = _make_session(seat, now, now + timedelta(minutes=3))  # within 5-min lead
    db.add(s)
    await db.commit()
    await db.refresh(s)
    with (
        patch("backend.services.session_service.remote_command_service") as rc,
        patch("backend.services.session_service.ws_manager") as ws,
    ):
        rc.force_overlay = AsyncMock()
        ws.send_to_agent = AsyncMock()
        ws.broadcast_to_dashboards = AsyncMock()
        await sweep_expired_sessions(db)
    # LOW_TIME_WARNING payload sent
    sent = [c.args[1]["type"] for c in ws.send_to_agent.await_args_list]
    assert "LOW_TIME_WARNING" in sent
    refreshed = await session_repo.get_by_id(db, s.id)
    assert refreshed.expiry_warned is True
    # second sweep does not re-warn
    ws.send_to_agent.reset_mock()
    await sweep_expired_sessions(db)
    sent_types = [c.args[1]["type"] for c in ws.send_to_agent.await_args_list]
    assert "LOW_TIME_WARNING" not in sent_types


async def test_paused_session_deferred(db, zone_and_seat):
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    s = _make_session(seat, now, now - timedelta(minutes=5))
    s.status = SessionStatus.PAUSED
    db.add(s)
    await db.commit()
    await db.refresh(s)
    with (
        patch("backend.services.session_service.remote_command_service") as rc,
        patch("backend.services.session_service.ws_manager") as ws,
    ):
        rc.force_overlay = AsyncMock()
        ws.send_to_agent = AsyncMock()
        await sweep_expired_sessions(db)
    rc.force_overlay.assert_not_awaited()
    assert (await seat_repo.get_by_id(db, seat.id)).status != SeatStatus.EXPIRED


async def test_no_assigned_end_untouched(db, zone_and_seat):
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    s = GamingSession(
        seat_id=seat.id,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model="PER_MINUTE",
        status=SessionStatus.ACTIVE,
    )
    db.add(s)
    await db.commit()
    with (
        patch("backend.services.session_service.remote_command_service") as rc,
        patch("backend.services.session_service.ws_manager") as ws,
    ):
        rc.force_overlay = AsyncMock()
        ws.send_to_agent = AsyncMock()
        await sweep_expired_sessions(db)
    rc.force_overlay.assert_not_awaited()
