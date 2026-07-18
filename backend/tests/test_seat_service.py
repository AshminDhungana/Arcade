"""Unit tests for :mod:`backend.services.seat_service`.

Covers all public business-logic functions with mocked WebSocket broadcasts.
Uses an in-memory async SQLite DB for repository calls.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import GamingSession, PricingModel, SeatStatus, SessionStatus, Staff
from backend.repositories import seat_repo, staff_repo
from backend.schemas.seat import SeatResponse
from backend.services.seat_service import (
    clear_maintenance,
    get_seat,
    list_seats,
    set_maintenance,
    update_mac_address,
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
    """Create a zone and a seat, return (zone, seat)."""
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
async def admin_staff(db: AsyncSession) -> Staff:
    """Create and return an Admin staff member."""
    return await staff_repo.create(
        db, name="Admin User", pin_hash="argon2id$", role="ADMIN"
    )


# -------------------------------------------------------------------
# list_seats
# -------------------------------------------------------------------


async def test_list_seats_empty(db: AsyncSession) -> None:
    """list_seats returns an empty list when no seats exist."""
    seats = await list_seats(db)
    assert seats == []


async def test_list_seats_returns_seats(db: AsyncSession, zone_and_seat) -> None:
    """list_seats returns all persisted seats."""
    _, seat = zone_and_seat
    seats = await list_seats(db)
    assert len(seats) == 1
    assert isinstance(seats[0], SeatResponse)
    assert seats[0].id == seat.id
    assert seats[0].name == "PC-01"


# -------------------------------------------------------------------
# get_seat
# -------------------------------------------------------------------


async def test_get_seat_found(db: AsyncSession, zone_and_seat) -> None:
    """get_seat returns the seat when it exists."""
    _, seat = zone_and_seat
    result = await get_seat(db, seat.id)
    assert isinstance(result, SeatResponse)
    assert result.id == seat.id


async def test_get_seat_not_found(db: AsyncSession) -> None:
    """get_seat raises 404 when the seat does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await get_seat(db, "non-existent-id")
    assert exc_info.value.status_code == 404
    assert "non-existent-id" in exc_info.value.detail


# -------------------------------------------------------------------
# set_maintenance
# -------------------------------------------------------------------


async def test_set_maintenance_ok(
    db: AsyncSession, zone_and_seat: tuple, admin_staff: Staff
) -> None:
    """set_maintenance marks a seat as MAINTENANCE and logs an audit entry."""
    _, seat = zone_and_seat
    with patch("backend.services.seat_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await set_maintenance(db, seat.id, "Fan broken", admin_staff)

    assert result.status == SeatStatus.MAINTENANCE
    assert result.notes == "Fan broken"
    mock_ws.broadcast_to_dashboards.assert_awaited_once()


async def test_set_maintenance_not_found(db: AsyncSession, admin_staff) -> None:
    """set_maintenance raises 404 when seat does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await set_maintenance(db, "ghost-id", "note", admin_staff)
    assert exc_info.value.status_code == 404


# -------------------------------------------------------------------
# clear_maintenance
# -------------------------------------------------------------------


async def test_clear_maintenance_ok(
    db: AsyncSession, zone_and_seat, admin_staff
) -> None:
    """clear_maintenance resets seat to AVAILABLE and logs audit entry."""
    _, seat = zone_and_seat

    # first put into maintenance
    with patch("backend.services.seat_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        await set_maintenance(db, seat.id, "Fan broken", admin_staff)
        mock_ws.reset_mock()

        # then clear
        result = await clear_maintenance(db, seat.id, admin_staff)

    assert result.status == SeatStatus.AVAILABLE
    assert result.notes is None
    mock_ws.broadcast_to_dashboards.assert_awaited_once()


async def test_clear_maintenance_not_found(db: AsyncSession, admin_staff) -> None:
    """clear_maintenance raises 404 when seat does not exist."""
    with patch("backend.services.seat_service.ws_manager"):
        with pytest.raises(HTTPException) as exc_info:
            await clear_maintenance(db, "ghost-id", admin_staff)
        assert exc_info.value.status_code == 404


# -------------------------------------------------------------------
# update_mac_address
# -------------------------------------------------------------------


async def test_update_mac_address_ok(db: AsyncSession, zone_and_seat) -> None:
    """update_mac_address sets mac_address and broadcasts the change."""
    _, seat = zone_and_seat
    with patch("backend.services.seat_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await update_mac_address(db, seat.id, "aa:bb:cc:dd:ee:ff")

    assert result.mac_address == "aa:bb:cc:dd:ee:ff"
    mock_ws.broadcast_to_dashboards.assert_awaited_once()


async def test_update_mac_address_none(db: AsyncSession, zone_and_seat) -> None:
    """update_mac_address can clear the MAC address when None is passed."""
    _, seat = zone_and_seat
    with patch("backend.services.seat_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await update_mac_address(db, seat.id, None)
    assert result.mac_address is None


async def test_update_mac_address_not_found(db: AsyncSession) -> None:
    """update_mac_address raises 404 when seat does not exist."""
    with patch("backend.services.seat_service.ws_manager"):
        with pytest.raises(HTTPException) as exc_info:
            await update_mac_address(db, "ghost-id", "aa:bb:cc:dd:ee:ff")
    assert exc_info.value.status_code == 404


# -------------------------------------------------------------------
# assigned_end_at enrichment (Epic 6.5.4)
# -------------------------------------------------------------------


async def test_list_seats_includes_assigned_end_at(
    db: AsyncSession, zone_and_seat
) -> None:
    """list_seats surfaces the active session's assigned_end_at."""
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    session = GamingSession(
        seat_id=seat.id,
        status=SessionStatus.ACTIVE,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model=PricingModel.PER_MINUTE,
        assigned_end_at=now + timedelta(minutes=45),
    )
    db.add(session)
    await db.commit()

    seats = await list_seats(db)
    match = next(s for s in seats if s.id == seat.id)
    assert match.assigned_end_at == session.assigned_end_at


async def test_get_seat_includes_assigned_end_at(
    db: AsyncSession, zone_and_seat
) -> None:
    """get_seat surfaces the active session's assigned_end_at."""
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    session = GamingSession(
        seat_id=seat.id,
        status=SessionStatus.ACTIVE,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model=PricingModel.PER_MINUTE,
        assigned_end_at=now + timedelta(minutes=20),
    )
    db.add(session)
    await db.commit()

    result = await get_seat(db, seat.id)
    assert result.assigned_end_at == session.assigned_end_at


async def test_seat_without_assigned_session_returns_none(
    db: AsyncSession, zone_and_seat
) -> None:
    """A seat whose active session has no assigned_end_at yields None."""
    _, seat = zone_and_seat
    now = datetime.now(UTC)
    session = GamingSession(
        seat_id=seat.id,
        status=SessionStatus.ACTIVE,
        started_at=now,
        locked_rate_paise=0,
        locked_pricing_model=PricingModel.PER_MINUTE,
        assigned_end_at=None,
    )
    db.add(session)
    await db.commit()

    seats = await list_seats(db)
    match = next(s for s in seats if s.id == seat.id)
    assert match.assigned_end_at is None

    result = await get_seat(db, seat.id)
    assert result.assigned_end_at is None
