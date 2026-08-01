"""Tests for ws_manager."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.core.database import AsyncSessionLocal
from backend.core.ws_manager import WebSocketManager
from backend.models import Seat, SeatStatus
from backend.models._enums import PricingModel
from backend.repositories import seat_repo, zone_repo


@pytest.mark.asyncio
async def test_handle_register_sets_seat_online():
    manager = WebSocketManager()
    
    # Setup: create a seat in OFFLINE status
    async with AsyncSessionLocal() as db:
        zone = await zone_repo.create(
            db,
            name="Test Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()
        seat = await seat_repo.create(db, name="Test Seat", zone_id=zone.id)
        seat.status = SeatStatus.OFFLINE
        await db.commit()
        seat_id = seat.id
    
    # Call _handle_register
    with patch("backend.core.ws_manager.manager", manager):
        result = await manager._handle_register(seat_id, {
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "hostname": "test-pc"
        })
    
    # Verify seat is now AVAILABLE (not OFFLINE)
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.AVAILABLE
    
    # Verify response
    assert result["type"] == "REGISTERED"


@pytest.mark.asyncio
async def test_disconnect_agent_sets_seat_offline():
    manager = WebSocketManager()
    
    # Setup: create a seat in AVAILABLE status
    async with AsyncSessionLocal() as db:
        zone = await zone_repo.create(
            db,
            name="Test Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()
        seat = await seat_repo.create(db, name="Test Seat", zone_id=zone.id)
        seat.status = SeatStatus.AVAILABLE
        await db.commit()
        seat_id = seat.id
    
    # Mock websocket connection
    mock_ws = AsyncMock()
    manager.agent_connections[seat_id] = mock_ws
    
    # Call disconnect_agent
    await manager.disconnect_agent(seat_id)
    
    # Verify seat is now OFFLINE
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.OFFLINE
    
    # Verify connection cleaned up
    assert seat_id not in manager.agent_connections


@pytest.mark.asyncio
async def test_tick_calls_disconnect_agent_on_timeout():
    """Verify _tick calls disconnect_agent for expired
    agents (which handles OFFLINE status)."""
    manager = WebSocketManager()
    manager.disconnect_agent = AsyncMock()
    manager.broadcast_to_dashboards = AsyncMock()
    
    # Add a fake agent connection
    mock_ws = AsyncMock()
    manager.agent_connections["seat1"] = mock_ws
    manager._pending_pongs.add("seat1")
    
    # Call _tick
    await manager._tick()
    
    # Verify disconnect_agent was called for the expired seat
    manager.disconnect_agent.assert_awaited_once_with("seat1")