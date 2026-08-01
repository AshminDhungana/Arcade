"""Tests for ws_manager."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.core.ws_manager import WebSocketManager
from backend.core.database import AsyncSessionLocal
from backend.models import Seat, SeatStatus
from backend.repositories import seat_repo, zone_repo
from backend.models._enums import PricingModel


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