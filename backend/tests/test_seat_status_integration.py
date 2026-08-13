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
    ONLINE -> disconnect sets OFFLINE"""
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

    # 2. Agent connects - REGISTER should set ONLINE
    manager = WebSocketManager()

    with patch("backend.core.ws_manager.manager", manager):
        await manager._handle_register(
            seat_id, {"mac_address": "aa:bb:cc:dd:ee:ff", "hostname": "test-pc"}
        )

    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.ONLINE

    # 3. Agent disconnects - should set OFFLINE
    await manager.disconnect_agent(seat_id)

    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.OFFLINE


@pytest.mark.asyncio
async def test_register_with_active_session_keeps_in_use():
    """C.8 crash recovery: REGISTER while a session is active must NOT clobber
    the live state to AVAILABLE/ONLINE — the seat stays IN_USE."""
    from datetime import UTC, datetime

    from backend.models import GamingSession

    async with AsyncSessionLocal() as db:
        # Clean slate
        await db.execute(text("DELETE FROM sessions"))
        await db.execute(text("DELETE FROM seats"))
        await db.commit()

        zone = await zone_repo.create(
            db,
            name="Crash Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()

        seat = await seat_repo.create(db, name="Crash Seat", zone_id=zone.id)
        await db.commit()
        seat_id = seat.id

        # The agent was disconnected mid-session -> seat shows OFFLINE
        seat.status = SeatStatus.OFFLINE
        session = GamingSession(
            seat_id=seat_id,
            started_at=datetime.now(UTC),
            locked_rate_paise=100,
            locked_pricing_model=PricingModel.PER_MINUTE,
        )
        db.add(session)
        await db.commit()

    manager = WebSocketManager()
    with patch("backend.core.ws_manager.manager", manager):
        await manager._handle_register(
            seat_id, {"mac_address": "aa:bb:cc:dd:ee:ff", "hostname": "crash-pc"}
        )

    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.IN_USE

    # Clean up the session so the next test starts fresh
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM sessions"))
        await db.execute(text("DELETE FROM seats"))
        await db.commit()


@pytest.mark.asyncio
async def test_register_preserves_reserved():
    """REGISTER must not clobber a RESERVED seat."""
    async with AsyncSessionLocal() as db:
        # Clean slate
        await db.execute(text("DELETE FROM seats"))
        await db.commit()

        zone = await zone_repo.create(
            db,
            name="Reserve Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()

        seat = await seat_repo.create(db, name="Reserved Seat", zone_id=zone.id)
        seat.status = SeatStatus.RESERVED
        await db.commit()
        seat_id = seat.id

    manager = WebSocketManager()
    with patch("backend.core.ws_manager.manager", manager):
        await manager._handle_register(
            seat_id, {"mac_address": "aa:bb:cc:dd:ee:ff", "hostname": "reserve-pc"}
        )

    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.RESERVED


@pytest.mark.asyncio
async def test_register_preserves_maintenance():
    """REGISTER must not clobber a seat under MAINTENANCE."""
    async with AsyncSessionLocal() as db:
        # Clean slate
        await db.execute(text("DELETE FROM seats"))
        await db.commit()

        zone = await zone_repo.create(
            db,
            name="Maint Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=5000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await db.commit()

        seat = await seat_repo.create(db, name="Maint Seat", zone_id=zone.id)
        seat.status = SeatStatus.MAINTENANCE
        await db.commit()
        seat_id = seat.id

    manager = WebSocketManager()
    with patch("backend.core.ws_manager.manager", manager):
        await manager._handle_register(
            seat_id, {"mac_address": "aa:bb:cc:dd:ee:ff", "hostname": "maint-pc"}
        )

    async with AsyncSessionLocal() as db:
        refreshed = await db.get(Seat, seat_id)
        assert refreshed.status == SeatStatus.MAINTENANCE
