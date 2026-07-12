"""Tests for :mod:`backend.services.remote_command_service`.

Uses an in-memory async SQLite DB for seat lookups and a mocked
WebSocketManager for command sends.
"""

from __future__ import annotations

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
