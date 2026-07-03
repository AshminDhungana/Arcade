"""Tests for :mod:`backend.services.wol_service`.

Covers magic packet construction, per-seat WoL triggering, override,
watchdog timeout, and the success callback.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.models import SeatStatus
from backend.repositories import seat_repo

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncSession:
    # StaticPool ensures every checkout of this in-memory sqlite engine
    # reuses the *same* underlying connection. Without it, the connection
    # used by ``create_all`` and the one used by the test session can be
    # different :memory: databases, which shows up as intermittent
    # "no such table" errors rather than a clean failure.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def zone_and_seat_with_mac(db: AsyncSession):
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(
        db, name="PC-01", zone_id=zone.id, mac_address="aa:bb:cc:dd:ee:ff"
    )
    return zone, seat


@pytest.fixture
async def zone_and_seat_no_mac(db: AsyncSession):
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(db, name="PC-02", zone_id=zone.id)
    return zone, seat


@pytest.fixture(autouse=True)
async def _clean_watchdogs():
    yield
    from backend.services import wol_service

    for task in list(wol_service._watchdogs.values()):
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    wol_service._watchdogs.clear()


# ---------------------------------------------------------------------------
# send_magic_packet
# ---------------------------------------------------------------------------


def test_send_magic_packet_formats_correctly() -> None:
    """Verify the magic packet structure (6x0xFF + 16xMAC)."""
    from backend.services.wol_service import send_magic_packet

    with patch("socket.socket") as mock_sock_class:
        mock_sock = MagicMock()
        mock_sock_class.return_value = mock_sock

        send_magic_packet("aa:bb:cc:dd:ee:ff")

        mock_sock.sendto.assert_called_once()
        call_args = mock_sock.sendto.call_args
        packet = call_args.args[0]
        assert len(packet) == 102  # 6 + 16*6
        assert packet[:6] == b"\xff" * 6
        assert packet[6:12] == b"\xaa\xbb\xcc\xdd\xee\xff"


def test_send_magic_packet_rejects_invalid_mac() -> None:
    """Invalid MAC should raise ValueError."""
    from backend.services.wol_service import send_magic_packet

    with pytest.raises(ValueError, match="Invalid MAC address"):
        send_magic_packet("not-a-mac")


# ---------------------------------------------------------------------------
# send_wol_to_seat
# ---------------------------------------------------------------------------


async def test_send_wol_to_seat_success(
    db: AsyncSession, zone_and_seat_with_mac
) -> None:
    """send_wol_to_seat sends a magic packet and sets seat to BOOTING."""
    from backend.services import wol_service

    _, seat = zone_and_seat_with_mac

    async def _noop_watchdog(*args, delay):  # noqa: ARG001
        pass

    with (
        patch.object(wol_service, "_broadcast_seat_update", new=AsyncMock()),
        patch.object(wol_service, "_watchdog", new=_noop_watchdog),
        patch("socket.socket") as mock_sock,
    ):
        mock_sock.return_value.__enter__ = MagicMock(
            return_value=mock_sock.return_value
        )
        mock_sock.return_value.__exit__ = MagicMock(return_value=False)

        result = await wol_service.send_wol_to_seat(db, seat.id)

    assert result.status == SeatStatus.BOOTING
    assert result.wol_attempts == 1


async def test_send_wol_to_seat_404(db: AsyncSession) -> None:
    """send_wol_to_seat raises 404 for unknown seat."""
    from backend.services.wol_service import send_wol_to_seat

    with pytest.raises(HTTPException) as exc_info:
        await send_wol_to_seat(db, "ghost-id")
    assert exc_info.value.status_code == 404


async def test_send_wol_to_seat_422_no_mac(
    db: AsyncSession, zone_and_seat_no_mac
) -> None:
    """send_wol_to_seat raises 422 if seat has no MAC."""
    from backend.services.wol_service import send_wol_to_seat

    _, seat = zone_and_seat_no_mac
    with pytest.raises(HTTPException) as exc_info:
        await send_wol_to_seat(db, seat.id)
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# boot_all_seats
# ---------------------------------------------------------------------------


async def test_boot_all_seats_sends_to_all_with_mac(
    db: AsyncSession, zone_and_seat_with_mac, zone_and_seat_no_mac
) -> None:
    """boot_all_seats sends magic packets only to seats with a MAC."""
    from backend.services import wol_service

    async def _noop_watchdog(*args, delay):  # noqa: ARG001
        pass

    with (
        patch.object(wol_service, "_broadcast_seat_update", new=AsyncMock()),
        patch.object(wol_service, "_watchdog", new=_noop_watchdog),
        patch("socket.socket") as mock_sock,
    ):
        mock_sock.return_value.__enter__ = MagicMock(
            return_value=mock_sock.return_value
        )
        mock_sock.return_value.__exit__ = MagicMock(return_value=False)

        result = await wol_service.boot_all_seats(db)

    # Only one seat had a MAC address
    assert len(result) == 1


# ---------------------------------------------------------------------------
# override_seat_online
# ---------------------------------------------------------------------------


async def test_override_seat_online_sets_available(
    db: AsyncSession, zone_and_seat_with_mac
) -> None:
    """override_seat_online marks seat as AVAILABLE and cancels watchdog."""
    from backend.services import wol_service

    _, seat = zone_and_seat_with_mac
    seat.status = SeatStatus.BOOTING
    await db.flush()

    with patch.object(
        wol_service, "_broadcast_seat_update", new=AsyncMock()
    ) as mock_bc:
        result = await wol_service.override_seat_online(db, seat.id)

    assert result.status == SeatStatus.AVAILABLE
    mock_bc.assert_awaited_once()


async def test_override_seat_online_404(db: AsyncSession) -> None:
    """override_seat_online raises 404 for unknown seat."""
    from backend.services.wol_service import override_seat_online

    with pytest.raises(HTTPException) as exc_info:
        await override_seat_online(db, "ghost-id")
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# wol_success_callback
# ---------------------------------------------------------------------------


async def test_wol_success_callback_updates_seat(
    db: AsyncSession, zone_and_seat_with_mac
) -> None:
    """wol_success_callback marks BOOTING seat as AVAILABLE and increments success."""
    from backend.services import wol_service

    _, seat = zone_and_seat_with_mac
    seat.status = SeatStatus.BOOTING
    await db.flush()

    # Set a fake watchdog task to verify cancellation
    fake_task = asyncio.ensure_future(asyncio.sleep(10))
    wol_service._watchdogs[seat.id] = fake_task

    with patch.object(
        wol_service, "_broadcast_seat_update", new=AsyncMock()
    ) as mock_bc:
        await wol_service.wol_success_callback(seat.id, db=db)

    # Refresh seat
    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.AVAILABLE
    assert refreshed.wol_successes == 1
    mock_bc.assert_awaited_once()
    # The fake task is cancelled by wol_success_callback
    assert fake_task.cancelled()


async def test_wol_success_callback_noop_when_not_booting(
    db: AsyncSession, zone_and_seat_with_mac
) -> None:
    """wol_success_callback does nothing if the seat is not in BOOTING."""
    from backend.services import wol_service

    _, seat = zone_and_seat_with_mac
    seat.status = SeatStatus.AVAILABLE
    await db.flush()

    with patch.object(
        wol_service, "_broadcast_seat_update", new=AsyncMock()
    ) as mock_bc:
        await wol_service.wol_success_callback(seat.id)

    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.AVAILABLE
    assert refreshed.wol_successes == 0
    mock_bc.assert_not_awaited()


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------


async def test_watchdog_sets_unreachable(
    db: AsyncSession, zone_and_seat_with_mac
) -> None:
    """_watchdog marks a BOOTING seat as UNREACHABLE."""
    from backend.services import wol_service

    _, seat = zone_and_seat_with_mac
    seat.status = SeatStatus.BOOTING
    await db.flush()

    with patch.object(
        wol_service, "_broadcast_seat_update", new=AsyncMock()
    ) as mock_bc:
        await wol_service._watchdog(seat.id, delay=0, db=db)

    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.UNREACHABLE
    assert refreshed.wol_failures == 1
    mock_bc.assert_awaited_once()


async def test_watchdog_noop_when_not_booting(
    db: AsyncSession, zone_and_seat_with_mac
) -> None:
    """_watchdog does nothing if the seat is already not BOOTING."""
    from backend.services import wol_service

    _, seat = zone_and_seat_with_mac
    seat.status = SeatStatus.AVAILABLE
    await db.flush()

    with patch.object(
        wol_service, "_broadcast_seat_update", new=AsyncMock()
    ) as mock_bc:
        await wol_service._watchdog(seat.id, delay=0)

    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.AVAILABLE
    assert refreshed.wol_failures == 0
    mock_bc.assert_not_awaited()
