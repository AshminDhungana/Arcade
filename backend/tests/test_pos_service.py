"""Unit tests for :mod:`backend.services.pos_service`.

Covers add_item, remove_item, and list_session_items with mocked
WebSocket broadcasts. Uses an in-memory async SQLite DB for repository calls.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import GamingSession, PricingModel, SessionStatus, Zone
from backend.repositories import (
    inventory_repo,
    seat_repo,
    staff_repo,
)
from backend.services import pos_service


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
    """Create and return an ADMIN staff member."""
    return await staff_repo.create(
        db, name="Admin User", pin_hash="argon2id$", role="ADMIN"
    )


@pytest.fixture
async def active_session(db: AsyncSession, zone_and_seat):
    """Create and return an ACTIVE gaming session."""
    _, seat = zone_and_seat
    sess = GamingSession(
        seat_id=seat.id,
        started_at=datetime.now(UTC),
        locked_rate_paise=50,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(sess)
    await db.flush()
    await db.refresh(sess)
    return sess


@pytest.fixture
async def menu_item(db: AsyncSession):
    """Create and return a menu item."""
    return await inventory_repo.create(
        db, name="Red Bull", category="Drink", price_paise=15000
    )


# ── add_item ──────────────────────────────────────────────────────────────


async def test_add_item_ok(db: AsyncSession, active_session, menu_item, staff_member):
    """Adding an item to an active session succeeds and locks the price."""
    with patch("backend.services.pos_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await pos_service.add_item(
            db,
            session_id=active_session.id,
            menu_item_id=menu_item.id,
            quantity=2,
            staff_id=staff_member.id,
        )

    assert result.session_id == active_session.id
    assert result.menu_item_id == menu_item.id
    assert result.quantity == 2
    assert result.unit_price_paise == menu_item.price_paise
    mock_ws.broadcast_to_dashboards.assert_awaited_once()


async def test_add_item_session_not_found(db: AsyncSession, menu_item, staff_member):
    """Adding to a non-existent session raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await pos_service.add_item(
            db,
            session_id="non-existent-id",
            menu_item_id=menu_item.id,
            quantity=1,
            staff_id=staff_member.id,
        )
    assert exc_info.value.status_code == 404


async def test_add_item_ended_session(
    db: AsyncSession, zone_and_seat, menu_item, staff_member
):
    """Adding to a completed session raises 400."""
    _, seat = zone_and_seat
    sess = GamingSession(
        seat_id=seat.id,
        started_at=datetime.now(UTC),
        locked_rate_paise=50,
        locked_pricing_model=PricingModel.PER_MINUTE,
        status=SessionStatus.COMPLETED,
        ended_at=datetime.now(UTC),
    )
    db.add(sess)
    await db.flush()
    await db.refresh(sess)

    with pytest.raises(HTTPException) as exc_info:
        await pos_service.add_item(
            db,
            session_id=sess.id,
            menu_item_id=menu_item.id,
            quantity=1,
            staff_id=staff_member.id,
        )
    assert exc_info.value.status_code == 400


async def test_add_item_menu_item_not_found(
    db: AsyncSession, active_session, staff_member
):
    """Adding a non-existent menu item raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await pos_service.add_item(
            db,
            session_id=active_session.id,
            menu_item_id="non-existent-id",
            quantity=1,
            staff_id=staff_member.id,
        )
    assert exc_info.value.status_code == 404


async def test_add_item_unavailable(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """Adding an unavailable item raises 400."""
    menu_item.is_available = False
    await inventory_repo.update(db, menu_item)

    with pytest.raises(HTTPException) as exc_info:
        await pos_service.add_item(
            db,
            session_id=active_session.id,
            menu_item_id=menu_item.id,
            quantity=1,
            staff_id=staff_member.id,
        )
    assert exc_info.value.status_code == 400


async def test_add_item_inventory_decrement(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """When enable_inventory is ON, stock decrements and out-of-stock
    unavailability is set."""
    menu_item.stock_quantity = 5
    menu_item.is_available = True
    await inventory_repo.update(db, menu_item)

    with patch("backend.services.pos_service.get_flag", return_value=True):
        with patch("backend.services.pos_service.ws_manager") as mock_ws:
            mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
            await pos_service.add_item(
                db,
                session_id=active_session.id,
                menu_item_id=menu_item.id,
                quantity=3,
                staff_id=staff_member.id,
            )

    updated = await inventory_repo.get_by_id(db, menu_item.id)
    assert updated.stock_quantity == 2
    assert updated.is_available is True


async def test_add_item_inventory_out_of_stock(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """When enable_inventory is ON and stock hits zero, the item becomes unavailable."""
    menu_item.stock_quantity = 3
    menu_item.is_available = True
    await inventory_repo.update(db, menu_item)

    with patch("backend.services.pos_service.get_flag", return_value=True):
        with patch("backend.services.pos_service.ws_manager") as mock_ws:
            mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
            await pos_service.add_item(
                db,
                session_id=active_session.id,
                menu_item_id=menu_item.id,
                quantity=3,
                staff_id=staff_member.id,
            )

    updated = await inventory_repo.get_by_id(db, menu_item.id)
    assert updated.stock_quantity == 0
    assert updated.is_available is False


async def test_add_item_insufficient_stock(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """Ordering more than available stock raises 400."""
    menu_item.stock_quantity = 2
    menu_item.is_available = True
    await inventory_repo.update(db, menu_item)

    with patch("backend.services.pos_service.get_flag", return_value=True):
        with pytest.raises(HTTPException) as exc_info:
            await pos_service.add_item(
                db,
                session_id=active_session.id,
                menu_item_id=menu_item.id,
                quantity=5,
                staff_id=staff_member.id,
            )
    assert exc_info.value.status_code == 400


async def test_add_item_price_locked(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """unit_price_paise is locked at the current menu item price."""
    menu_item.price_paise = 20000
    await inventory_repo.update(db, menu_item)

    with patch("backend.services.pos_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await pos_service.add_item(
            db,
            session_id=active_session.id,
            menu_item_id=menu_item.id,
            quantity=1,
            staff_id=staff_member.id,
        )

    assert result.unit_price_paise == 20000


# ── remove_item ───────────────────────────────────────────────────────────


async def test_remove_item_ok(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """Removing a POS item succeeds."""
    with patch("backend.services.pos_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        created = await pos_service.add_item(
            db,
            session_id=active_session.id,
            menu_item_id=menu_item.id,
            quantity=2,
            staff_id=staff_member.id,
        )

    with patch("backend.services.pos_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await pos_service.remove_item(
            db,
            pos_item_id=created.id,
            session_id=active_session.id,
            staff_id=staff_member.id,
        )
    assert result is True


async def test_remove_item_not_found(db: AsyncSession, active_session, staff_member):
    """Removing a non-existent item returns False."""
    result = await pos_service.remove_item(
        db,
        pos_item_id="non-existent-id",
        session_id=active_session.id,
        staff_id=staff_member.id,
    )
    assert result is False


async def test_remove_item_wrong_session(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """Removing an item from a different session raises 400."""
    with patch("backend.services.pos_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        created = await pos_service.add_item(
            db,
            session_id=active_session.id,
            menu_item_id=menu_item.id,
            quantity=1,
            staff_id=staff_member.id,
        )

    other_session = GamingSession(
        seat_id=active_session.seat_id,
        started_at=datetime.now(UTC),
        locked_rate_paise=50,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(other_session)
    await db.flush()
    await db.refresh(other_session)

    with pytest.raises(HTTPException) as exc_info:
        await pos_service.remove_item(
            db,
            pos_item_id=created.id,
            session_id=other_session.id,
            staff_id=staff_member.id,
        )
    assert exc_info.value.status_code == 400


# ── list_session_items ────────────────────────────────────────────────────


async def test_list_session_items(
    db: AsyncSession, active_session, menu_item, staff_member
):
    """list_session_items returns all POS items for a session."""
    with patch("backend.services.pos_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        await pos_service.add_item(
            db,
            session_id=active_session.id,
            menu_item_id=menu_item.id,
            quantity=3,
            staff_id=staff_member.id,
        )

    items = await pos_service.list_session_items(db, session_id=active_session.id)
    assert len(items) == 1
    assert items[0].quantity == 3
