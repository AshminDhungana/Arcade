"""End-to-end lifecycle test for Epic 6.5.4 assigned-time auto-overlay.

This is the automated analogue of the manual scenario in docs/TODO.md:

    set a 2-minute assigned limit
      -> LOW_TIME_WARNING at 1 minute remaining
      -> overlay auto-shows (seat EXPIRED) at 0
      -> "Add time" resumes correctly with continuous billed-time accounting

The clock is simulated so the sweep + extend run at deterministic instants,
and the *real* `force_overlay` path executes (only the agent WebSocket send,
dashboard broadcasts, and audit writes are stubbed) so that the pause/resume
accrual in `total_paused_seconds` is genuinely exercised.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core import feature_flags
from backend.core.database import Base
from backend.core.ws_manager import Msg
from backend.models import SeatStatus, SessionStatus
from backend.repositories import seat_repo, session_repo
from backend.services import remote_command_service
from backend.services.session_service import (
    extend_session,
    start_session,
    sweep_expired_sessions,
)

# Simulated clock.  `datetime` itself is immutable (cannot patch `.now` on the
# class), so we subclass it and override `.now()` to read a mutable dict.  Because
# FakeDateTime *is a* datetime, every other use (constructors, arithmetic,
# `.replace`, `isinstance`) keeps working for both services under test.
CLOCK = {"now": datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)}


class FakeDateTime(datetime):
    @classmethod
    def now(cls, tz: object = None) -> datetime:
        return CLOCK["now"]


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
async def seat(db: AsyncSession):
    """Create a zone + seat; return the seat."""
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    return await seat_repo.create(db, name="PC-01", zone_id=zone.id)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Stub the agent/broadcast/audit boundaries and the simulated clock."""
    monkeypatch.setattr(
        "backend.services.remote_command_service._send_to_agent_or_503", AsyncMock()
    )
    monkeypatch.setattr(
        "backend.core.ws_manager.manager.broadcast_to_dashboards", AsyncMock()
    )
    monkeypatch.setattr("backend.services.audit_service.log", AsyncMock())
    monkeypatch.setattr("backend.core.ws_manager.manager.send_to_agent", AsyncMock())
    # Patch the `datetime` name in each service module with FakeDateTime so their
    # `datetime.now(UTC)` calls read CLOCK.  Module attributes are mutable.
    monkeypatch.setattr("backend.services.session_service.datetime", FakeDateTime)
    monkeypatch.setattr(
        "backend.services.remote_command_service.datetime", FakeDateTime
    )
    # force_overlay routes through pause accounting only when this is ON.
    feature_flags._flag_cache["overlay_pauses_billing"] = True
    yield
    feature_flags._flag_cache.pop("overlay_pauses_billing", None)


async def test_e2e_assigned_time_lifecycle(db, seat):
    t0 = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)

    # --- Start: 2-minute assigned limit ---
    CLOCK["now"] = t0
    session = await start_session(
        db, seat.id, None, None, time_now=t0, assigned_minutes=2
    )
    assert session.assigned_end_at is not None
    # Seat is still IN_USE; not yet expired.
    assert (await seat_repo.get_by_id(db, seat.id)).status == SeatStatus.IN_USE

    # --- 1 minute in: inside the warning window (lead default 5 min) ---
    CLOCK["now"] = t0 + timedelta(minutes=1)
    await sweep_expired_sessions(db)
    s1 = await session_repo.get_by_id(db, session.id)
    assert s1.expiry_warned is True  # LOW_TIME_WARNING was sent
    assert (await seat_repo.get_by_id(db, seat.id)).status == SeatStatus.IN_USE
    assert s1.status == SessionStatus.ACTIVE  # not expired yet

    # --- 2 minutes in: deadline reached -> overlay on, seat EXPIRED ---
    # The REAL force_overlay runs here (only agent-send / broadcast / audit are
    # stubbed), so the pause-accounting path executes for real.
    CLOCK["now"] = t0 + timedelta(minutes=2)
    await sweep_expired_sessions(db)
    sends = remote_command_service._send_to_agent_or_503
    assert len(sends.await_args_list) == 1
    assert sends.await_args_list[0].args[1]["type"] == Msg.FORCE_OVERLAY_ON
    expired_seat = await seat_repo.get_by_id(db, seat.id)
    assert expired_seat.status == SeatStatus.EXPIRED
    s2 = await session_repo.get_by_id(db, session.id)
    assert s2.status == SessionStatus.PAUSED  # paused by the forced overlay
    assert s2.total_paused_seconds == 0  # pause just began; nothing accrued yet

    # --- 3 minutes later: "Add time" (+5 min) resumes the seat ---
    # Again the REAL force_overlay runs (show=False) -> resume + accrual.
    CLOCK["now"] = t0 + timedelta(minutes=5)  # 3 min after expiry
    extended = await extend_session(db, session.id, 5, None)
    sends = remote_command_service._send_to_agent_or_503
    assert len(sends.await_args_list) == 2
    assert sends.await_args_list[1].args[1]["type"] == Msg.FORCE_OVERLAY_OFF

    # Continuous billing: same session, original start, paused gap accrued.
    resumed_seat = await seat_repo.get_by_id(db, seat.id)
    assert resumed_seat.status == SeatStatus.IN_USE  # reverted from EXPIRED
    s3 = await session_repo.get_by_id(db, session.id)
    assert s3.id == session.id  # one continuous session, not restarted
    assert s3.started_at == t0  # started_at preserved across the pause
    assert s3.status == SessionStatus.ACTIVE  # resumed
    assert s3.expiry_warned is False
    # The 3-minute expired gap was accrued as paused time (180 s).
    assert s3.total_paused_seconds == 180
    # Deadline pushed forward by the 5 minutes added.
    assert extended.assigned_end_at is not None
    assert extended.assigned_end_at == t0 + timedelta(minutes=7)
