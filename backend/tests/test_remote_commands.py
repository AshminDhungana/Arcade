"""Tests for :mod:`backend.services.remote_command_service`.

Uses an in-memory async SQLite DB for seat lookups and a mocked
WebSocketManager for command sends.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.repositories import seat_repo

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
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
async def zone_and_seat(db: AsyncSession):
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
def staff_member():
    from backend.models._enums import StaffRole

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock Cashier"
        is_active = True
        token_version = 0
        role = StaffRole("CASHIER")

    return _MockStaff()


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------


async def test_send_message_sends_and_audits(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """send_message sends SHOW_MESSAGE and audits MESSAGE_SENT."""
    from backend.core.ws_manager import Msg
    from backend.models._enums import AuditAction
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat

    with (
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()) as mock_send,
        patch.object(rcs.audit_service, "log", new=AsyncMock()) as mock_audit,
    ):
        await rcs.send_message(db, seat.id, "Please logout", staff_member)

    mock_send.assert_awaited_once()
    sent = mock_send.call_args.args[1]
    assert sent["type"] == Msg.SHOW_MESSAGE
    assert sent["payload"]["text"] == "Please logout"
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["action"] == AuditAction.MESSAGE_SENT


async def test_send_message_offline_raises_503(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """send_message raises 503 when the agent is offline."""
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat
    with patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()) as mock_send:
        mock_send.side_effect = rcs.AgentOfflineError(seat.id)
        with pytest.raises(HTTPException) as exc_info:
            await rcs.send_message(db, seat.id, "hi", staff_member)
    assert exc_info.value.status_code == 503


async def test_send_message_seat_not_found(db: AsyncSession, staff_member) -> None:
    """send_message raises 404 for an unknown seat."""
    from backend.services import remote_command_service as rcs

    with pytest.raises(HTTPException) as exc_info:
        await rcs.send_message(db, "ghost-id", "hi", staff_member)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# request_screenshot
# ---------------------------------------------------------------------------


async def test_request_screenshot_returns_bytes_and_audits(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """request_screenshot returns JPEG bytes and audits SCREENSHOT_TAKEN."""
    from backend.models._enums import AuditAction
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat
    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\xff\xd9"

    with (
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(
            rcs.ws_manager, "wait_for_screenshot", new=AsyncMock(return_value=fake_jpeg)
        ) as mock_wait,
        patch.object(rcs.audit_service, "log", new=AsyncMock()) as mock_audit,
        patch("backend.services.remote_command_service.uuid") as mock_uuid,
    ):
        mock_uuid.uuid4.return_value.hex = "req-abc"
        data = await rcs.request_screenshot(db, seat.id, staff_member)

    assert data == fake_jpeg
    # wait_for_screenshot is called with request_id, seat_id=seat_id, timeout
    mock_wait.assert_awaited_once()
    args, kwargs = mock_wait.call_args
    assert args[0] == "req-abc"
    assert kwargs.get("timeout") == rcs.SCREENSHOT_TIMEOUT
    assert mock_audit.call_args.kwargs["action"] == AuditAction.SCREENSHOT_TAKEN


async def test_request_screenshot_rate_limited(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """A 2nd concurrent request for the same seat is rejected with 409."""
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat

    # First call hangs on the await (future never resolved).
    async def _hang(*args, **kwargs):
        await asyncio.sleep(10)

    with (
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(rcs.ws_manager, "wait_for_screenshot", new=_hang),
        patch("backend.services.remote_command_service.uuid") as mock_uuid,
    ):
        mock_uuid.uuid4.return_value.hex = "req-first"
        first = asyncio.create_task(rcs.request_screenshot(db, seat.id, staff_member))
        # Let the first call register its in-flight lock.
        await asyncio.sleep(0.2)
        with pytest.raises(HTTPException) as exc_info:
            await rcs.request_screenshot(db, seat.id, staff_member)
        assert exc_info.value.status_code == 409
        # Clean up the still-hanging first task.
        first.cancel()
        try:
            await first
        except (asyncio.CancelledError, rcs.ScreenshotTimeoutError):
            pass


async def test_request_screenshot_timeout_504(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """A screenshot with no agent response times out → 504."""
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat

    async def _timeout(*args, **kwargs):
        raise asyncio.TimeoutError()  # noqa: UP041

    with (
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(rcs.ws_manager, "wait_for_screenshot", new=_timeout),
        patch("backend.services.remote_command_service.uuid") as mock_uuid,
    ):
        mock_uuid.uuid4.return_value.hex = "req-timeout"
        with pytest.raises(HTTPException) as exc_info:
            await rcs.request_screenshot(db, seat.id, staff_member)
    assert exc_info.value.status_code == 504


async def test_request_screenshot_invalid_image_502(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """Non-JPEG response data is rejected with 502."""
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat

    with (
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(
            rcs.ws_manager,
            "wait_for_screenshot",
            new=AsyncMock(return_value=b"not-an-image"),
        ),
        patch("backend.services.remote_command_service.uuid") as mock_uuid,
    ):
        mock_uuid.uuid4.return_value.hex = "req-bad"
        with pytest.raises(HTTPException) as exc_info:
            await rcs.request_screenshot(db, seat.id, staff_member)
    assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# restart_seat / shutdown_seat
# ---------------------------------------------------------------------------


async def test_restart_seat_sends_and_audits(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """restart_seat sends RESTART and audits SEAT_RESTARTED."""
    from backend.models._enums import AuditAction
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat
    with (
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()) as mock_send,
        patch.object(rcs.audit_service, "log", new=AsyncMock()) as mock_audit,
    ):
        await rcs.restart_seat(db, seat.id, staff_member)
    sent = mock_send.call_args.args[1]
    assert sent["type"] == rcs.Msg.RESTART
    assert sent["payload"]["delay_seconds"] == rcs.COMMAND_DELAY_SECONDS
    assert mock_audit.call_args.kwargs["action"] == AuditAction.SEAT_RESTARTED


async def test_shutdown_seat_sends_and_audits(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """shutdown_seat sends SHUTDOWN and audits SEAT_SHUTDOWN."""
    from backend.models._enums import AuditAction
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat
    with (
        patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()) as mock_send,
        patch.object(rcs.audit_service, "log", new=AsyncMock()) as mock_audit,
    ):
        await rcs.shutdown_seat(db, seat.id, staff_member)
    sent = mock_send.call_args.args[1]
    assert sent["type"] == rcs.Msg.SHUTDOWN
    assert mock_audit.call_args.kwargs["action"] == AuditAction.SEAT_SHUTDOWN


async def test_restart_seat_offline_503(
    db: AsyncSession, zone_and_seat, staff_member
) -> None:
    """restart_seat raises 503 when the agent is offline."""
    from backend.services import remote_command_service as rcs

    _, seat = zone_and_seat
    with patch.object(rcs.ws_manager, "send_to_agent", new=AsyncMock()) as mock_send:
        mock_send.side_effect = rcs.AgentOfflineError(seat.id)
        with pytest.raises(HTTPException) as exc_info:
            await rcs.restart_seat(db, seat.id, staff_member)
    assert exc_info.value.status_code == 503


async def test_shutdown_seat_not_found(db: AsyncSession, staff_member) -> None:
    """shutdown_seat raises 404 for an unknown seat."""
    from backend.services import remote_command_service as rcs

    with pytest.raises(HTTPException) as exc_info:
        await rcs.shutdown_seat(db, "ghost-id", staff_member)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# set_overlay_forced
# ---------------------------------------------------------------------------


async def test_set_overlay_forced_sets_and_broadcasts(
    db: AsyncSession, zone_and_seat
) -> None:
    """set_overlay_forced flips the flag, commits, and broadcasts seat_updated."""
    from backend.services import seat_service

    _, seat = zone_and_seat
    resp = await seat_service.set_overlay_forced(db, seat.id, True)
    assert resp.overlay_forced is True

    # Re-read from DB to confirm persistence.
    refreshed = await seat_service.get_seat(db, seat.id)
    assert refreshed.overlay_forced is True

    resp_off = await seat_service.set_overlay_forced(db, seat.id, False)
    assert resp_off.overlay_forced is False


async def test_set_overlay_forced_missing_seat_404(
    db: AsyncSession,
) -> None:
    """set_overlay_forced raises 404 for an unknown seat."""
    from fastapi import HTTPException

    from backend.services import seat_service

    with pytest.raises(HTTPException) as exc_info:
        await seat_service.set_overlay_forced(db, "ghost-id", True)
    assert exc_info.value.status_code == 404
