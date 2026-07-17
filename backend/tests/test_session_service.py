"""Unit tests for :mod:`backend.services.session_service`.

Covers all public business-logic functions with mocked WebSocket broadcasts.
Uses an in-memory async SQLite DB for repository calls.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import SeatStatus, SessionStatus
from backend.models._enums import ShiftStatus
from backend.repositories import seat_repo, shift_repo, staff_repo
from backend.services.session_service import (
    get_session,
    list_active_sessions,
    pause_session,
    recover_active_sessions,
    resume_session,
    start_session,
)

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


@pytest.fixture
async def staff_member(db: AsyncSession):
    """Create and return a CASHIER staff member."""
    return await staff_repo.create(
        db, name="Cashier User", pin_hash="argon2id$", role="CASHIER"
    )


# -------------------------------------------------------------------
# start_session
# -------------------------------------------------------------------


async def test_start_session_ok(db: AsyncSession, zone_and_seat, staff_member):
    """start_session creates an ACTIVE session, marks seat as IN_USE, and broadcasts."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        result = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )

    assert result.seat_id == seat.id
    assert result.status == SessionStatus.ACTIVE
    mock_ws.broadcast_to_dashboards.assert_awaited_once()
    mock_ws.send_to_agent.assert_awaited_once()


async def test_start_session_seat_not_found(db: AsyncSession, staff_member):
    """start_session raises 404 for a missing seat."""
    with pytest.raises(HTTPException) as exc_info:
        await start_session(
            db, seat_id="non-existent-id", member_id=None, staff=staff_member
        )
    assert exc_info.value.status_code == 404


async def test_start_session_seat_unavailable(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session raises 409 when seat is not AVAILABLE or RESERVED."""
    _, seat = zone_and_seat
    seat.status = SeatStatus.MAINTENANCE
    await seat_repo.update(db, seat)

    with pytest.raises(HTTPException) as exc_info:
        await start_session(db, seat_id=seat.id, member_id=None, staff=staff_member)
    assert exc_info.value.status_code == 409
    assert "SEAT_UNAVAILABLE" in exc_info.value.detail


async def test_start_session_member_required(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session raises 400 when require_member_for_session flag
    is set and member_id is None.
    """
    _, seat = zone_and_seat
    with patch(
        "backend.services.session_service.get_flag",
        side_effect=lambda key: True if key == "require_member_for_session" else False,
    ):  # type: ignore[override]
        with pytest.raises(HTTPException) as exc_info:
            await start_session(db, seat_id=seat.id, member_id=None, staff=staff_member)
    assert exc_info.value.status_code == 400


async def test_start_session_without_member_allowed_when_flag_off(
    db: AsyncSession, zone_and_seat, staff_member
):
    """Session starts with member_id=None when require_member_for_session is off."""
    _, seat = zone_and_seat
    with patch(
        "backend.services.session_service.get_flag",
        side_effect=lambda key: False,
    ):  # type: ignore[override]
        with patch("backend.services.session_service.ws_manager") as mock_ws:
            mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
            mock_ws.send_to_agent = AsyncMock(return_value=None)
            result = await start_session(
                db, seat_id=seat.id, member_id=None, staff=staff_member
            )
    assert result.status == SessionStatus.ACTIVE
    assert result.member_id is None


async def test_start_session_links_package_entitlement(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session links active package entitlement when member has one."""
    from backend.models import EntitlementStatus, MemberPackageEntitlement
    from backend.repositories import member_repo, package_repo

    _, seat = zone_and_seat
    member = await member_repo.create(db, name="Alice", phone="555-0001")
    pkg = await package_repo.create(
        db,
        name="Hour Pack",
        type="HOUR_BUNDLE",
        total_minutes=60,
        price_paise=5000,
    )
    entitlement = MemberPackageEntitlement(
        member_id=member.id,
        package_id=pkg.id,
        remaining_minutes=60,
        status=EntitlementStatus.ACTIVE,
    )
    db.add(entitlement)
    await db.flush()
    await db.refresh(entitlement)

    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        result = await start_session(
            db, seat_id=seat.id, member_id=member.id, staff=staff_member
        )

    assert result.package_entitlement_id == entitlement.id


async def test_start_session_without_member_no_entitlement(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session leaves package_entitlement_id None when no member."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        result = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )

    assert result.package_entitlement_id is None


async def test_start_session_existing_active(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session raises 409 when an active session already exists for the seat."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        await start_session(db, seat_id=seat.id, member_id=None, staff=staff_member)

        with pytest.raises(HTTPException) as exc_info:
            await start_session(db, seat_id=seat.id, member_id=None, staff=staff_member)
        assert exc_info.value.status_code == 409
        assert "ACTIVE_SESSION_EXISTS" in exc_info.value.detail


async def test_start_session_links_current_open_shift(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session stamps shift_id from the currently open shift."""
    shift = await shift_repo.create(
        db,
        opened_by_staff_id=staff_member.id,
        opened_at=datetime.now(UTC),
        float_paise=5000,
        status=ShiftStatus.OPEN,
    )
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        result = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )
    assert result.shift_id == shift.id


async def test_start_session_no_shift_id_when_none_open(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session leaves shift_id None when no shift is open."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        result = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )
    assert result.shift_id is None


# -------------------------------------------------------------------
# pause_session – invalid state
# -------------------------------------------------------------------


async def test_pause_session_ok(db: AsyncSession, zone_and_seat, staff_member):
    """pause_session changes status to PAUSED and broadcasts/shows overlay."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        session = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )
        mock_ws.reset_mock()

        result = await pause_session(db, session_id=session.id, staff=staff_member)

    assert result.status == SessionStatus.PAUSED
    mock_ws.broadcast_to_dashboards.assert_awaited_once()
    mock_ws.send_to_agent.assert_awaited_once()


async def test_pause_session_not_found(db: AsyncSession, staff_member):
    """pause_session raises 404 for a missing session."""
    with pytest.raises(HTTPException) as exc_info:
        await pause_session(db, session_id="non-existent-id", staff=staff_member)
    assert exc_info.value.status_code == 404


async def test_pause_session_invalid_state(
    db: AsyncSession, zone_and_seat, staff_member
):
    """pause_session raises 409 when session is not ACTIVE."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        session = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )

        # pause then pause again
        await pause_session(db, session_id=session.id, staff=staff_member)
        with pytest.raises(HTTPException) as exc_info:
            await pause_session(db, session_id=session.id, staff=staff_member)
        assert exc_info.value.status_code == 409


# -------------------------------------------------------------------
# resume_session
# -------------------------------------------------------------------


async def test_resume_session_ok(db: AsyncSession, zone_and_seat, staff_member):
    """resume_session changes PAUSED to ACTIVE and accumulates paused time."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        sess = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )
        await pause_session(db, session_id=sess.id, staff=staff_member)
        mock_ws.reset_mock()

        resumed = await resume_session(db, session_id=sess.id, staff=staff_member)

    assert resumed.status == SessionStatus.ACTIVE
    assert resumed.total_paused_seconds >= 0
    mock_ws.broadcast_to_dashboards.assert_awaited_once()
    mock_ws.send_to_agent.assert_awaited_once()


async def test_resume_session_not_found(db: AsyncSession, staff_member):
    """resume_session raises 404 for a missing session."""
    with pytest.raises(HTTPException) as exc_info:
        await resume_session(db, session_id="non-existent-id", staff=staff_member)
    assert exc_info.value.status_code == 404


async def test_resume_session_invalid_state(
    db: AsyncSession, zone_and_seat, staff_member
):
    """resume_session raises 409 when session is not PAUSED."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        session = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )

        with pytest.raises(HTTPException) as exc_info:
            await resume_session(db, session_id=session.id, staff=staff_member)
        assert exc_info.value.status_code == 409


# -------------------------------------------------------------------
# get_session
# -------------------------------------------------------------------


async def test_get_session_found(db: AsyncSession, zone_and_seat, staff_member):
    """get_session returns the session when it exists."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        session = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )

    result = await get_session(db, session_id=session.id)
    assert result.id == session.id


async def test_get_session_not_found(db: AsyncSession):
    """get_session raises 404 when the session does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await get_session(db, session_id="non-existent-id")
    assert exc_info.value.status_code == 404


# -------------------------------------------------------------------
# list_active_sessions
# -------------------------------------------------------------------


async def test_list_active_sessions_empty(db: AsyncSession):
    """list_active_sessions returns an empty list when nothing is active."""
    sessions = await list_active_sessions(db)
    assert sessions == []


async def test_list_active_sessions_with_data(
    db: AsyncSession, zone_and_seat, staff_member
):
    """list_active_sessions returns both active and paused sessions."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        session = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )

    sessions = await list_active_sessions(db)
    assert len(sessions) == 1
    assert sessions[0].id == session.id


# -------------------------------------------------------------------
# recover_active_sessions
# -------------------------------------------------------------------


async def test_recover_active_sessions(db: AsyncSession, zone_and_seat, staff_member):
    """recover_active_sessions broadcasts seat status for active sessions."""
    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        await start_session(db, seat_id=seat.id, member_id=None, staff=staff_member)

        await recover_active_sessions(db)

    # Should broadcast for the active session
    mock_ws.broadcast_to_dashboards.assert_awaited()


# -------------------------------------------------------------------
# self-correcting overlay_forced clearing (Task 5)
# -------------------------------------------------------------------


async def test_start_session_clears_overlay_forced(
    db: AsyncSession, zone_and_seat, staff_member
):
    """start_session clears overlay_forced after sending HIDE_OVERLAY."""
    from backend.services import seat_service

    _, seat = zone_and_seat
    # Pre-set overlay_forced to True (as if force-locked before session start)
    await seat_service.set_overlay_forced(db, seat.id, True)
    assert (await seat_service.get_seat(db, seat.id)).overlay_forced is True

    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        await start_session(db, seat_id=seat.id, member_id=None, staff=staff_member)

    # overlay_forced should be cleared to False
    assert (await seat_service.get_seat(db, seat.id)).overlay_forced is False


async def test_resume_session_clears_overlay_forced(
    db: AsyncSession, zone_and_seat, staff_member
):
    """resume_session clears overlay_forced after sending HIDE_OVERLAY."""
    from backend.services import seat_service

    _, seat = zone_and_seat
    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        sess = await start_session(
            db, seat_id=seat.id, member_id=None, staff=staff_member
        )
        await pause_session(db, session_id=sess.id, staff=staff_member)

    # Force it back to True before resume
    await seat_service.set_overlay_forced(db, seat.id, True)
    assert (await seat_service.get_seat(db, seat.id)).overlay_forced is True

    with patch("backend.services.session_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        mock_ws.send_to_agent = AsyncMock(return_value=None)
        await resume_session(db, session_id=sess.id, staff=staff_member)

    # overlay_forced should be cleared to False after resume
    assert (await seat_service.get_seat(db, seat.id)).overlay_forced is False
