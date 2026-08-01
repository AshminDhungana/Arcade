"""Integration tests for seat online/offline status cycle."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import text

from backend.core.database import AsyncSessionLocal
from backend.core.startup import initialize_seat_statuses
from backend.core.ws_manager import WebSocketManager
from backend.models import Seat, SeatStatus
from backend.models._enums import PricingModel
from backend.repositories import seat_repo, zone_repo


@pytest.mark.asyncio
async def test_new_seat_starts_offline():
    """Newly created seat should start as OFFLINE, not AVAILABLE."""
    async with AsyncSessionLocal() as db:
        # Clean slate
        await db.execute(text("DELETE FROM seats"))
        await db.commit()
        
        # Create a zone
        zone = await zone_repo.create(
            db,
            name="Test Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()
        
        # Create test seat via repository
        seat = await seat_repo.create(db, name="New Seat", zone_id=zone.id)
        await db.commit()
        
        # Verify seat starts as OFFLINE
        assert seat.status == SeatStatus.OFFLINE


@pytest.mark.asyncio
async def test_full_online_offline_cycle():
    """Test: startup sets OFFLINE -> register sets
    AVAILABLE -> disconnect sets OFFLINE"""
    async with AsyncSessionLocal() as db:
        # Clean slate
        await db.execute(text("DELETE FROM seats"))
        await db.commit()
        
        # Create a zone
        zone = await zone_repo.create(
            db,
            name="Integration Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()
        
        # Create test seat
        seat = await seat_repo.create(db, name="Integration Seat", zone_id=zone.id)
        seat.status = SeatStatus.AVAILABLE  # Simulate previous state
        await db.commit()
        seat_id = seat.id
    
    # 1. Startup initialization - should set to OFFLINE
    await initialize_seat_statuses()
    
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.OFFLINE
    
    # 2. Agent connects - REGISTER should set AVAILABLE
    manager = WebSocketManager()
    
    with patch("backend.core.ws_manager.manager", manager):
        await manager._handle_register(seat_id, {
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "hostname": "test-pc"
        })
    
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.AVAILABLE
    
    # 3. Agent disconnects - should set OFFLINE
    await manager.disconnect_agent(seat_id)
    
    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.OFFLINE