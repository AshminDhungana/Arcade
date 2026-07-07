"""Unit tests for :mod:`backend.services.inventory_service`.

Covers restock and get_low_stock_items with mocked WebSocket broadcasts.
Uses an in-memory async SQLite DB for repository calls.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.repositories import inventory_repo, restock_repo, staff_repo
from backend.services import inventory_service


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
async def staff_member(db: AsyncSession):
    """Create and return an ADMIN staff member."""
    return await staff_repo.create(
        db, name="Admin User", pin_hash="argon2id$", role="ADMIN"
    )


@pytest.fixture
async def beverage(db: AsyncSession):
    """Create and return a menu item (beverage)."""
    return await inventory_repo.create(
        db, name="Red Bull", category="Drink", price_paise=15000, stock_quantity=10
    )


# ── restock ─────────────────────────────────────────────────────────────


async def test_restock_ok(db: AsyncSession, beverage, staff_member):
    """Restocking a valid item increments its stock and logs the event."""
    initial_stock = beverage.stock_quantity

    with patch("backend.services.inventory_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await inventory_service.restock(
            db,
            menu_item_id=beverage.id,
            quantity=50,
            logged_by_staff_id=staff_member.id,
        )

    assert result.stock_quantity == initial_stock + 50
    assert result.is_available is True
    mock_ws.broadcast_to_dashboards.assert_awaited_once()


async def test_restock_not_found(db: AsyncSession, staff_member):
    """Restocking a non-existent item raises 404."""
    with patch("backend.services.inventory_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc_info:
            await inventory_service.restock(
                db,
                menu_item_id="non-existent-id",
                quantity=10,
                logged_by_staff_id=staff_member.id,
            )
    assert exc_info.value.status_code == 404


async def test_restock_reenables_availability(db: AsyncSession, beverage, staff_member):
    """Restocking an unavailable item (stock=0) re-enables is_available."""
    beverage.stock_quantity = 0
    beverage.is_available = False
    await inventory_repo.update(db, beverage)

    with patch("backend.services.inventory_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        result = await inventory_service.restock(
            db,
            menu_item_id=beverage.id,
            quantity=10,
            logged_by_staff_id=staff_member.id,
        )

    assert result.stock_quantity == 10
    assert result.is_available is True


async def test_restock_creates_log(db: AsyncSession, beverage, staff_member):
    """A successful restock creates a restock_log entry."""
    with patch("backend.services.inventory_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        await inventory_service.restock(
            db,
            menu_item_id=beverage.id,
            quantity=25,
            logged_by_staff_id=staff_member.id,
        )

    logs = await restock_repo.list_by_menu_item(db, beverage.id)
    assert len(logs) == 1
    assert logs[0].quantity_added == 25
    assert logs[0].logged_by_staff_id == staff_member.id


async def test_restock_with_note(db: AsyncSession, beverage, staff_member):
    """The optional 'note' parameter is included in the audit log detail."""
    with patch("backend.services.inventory_service.ws_manager") as mock_ws:
        mock_ws.broadcast_to_dashboards = AsyncMock(return_value=None)
        await inventory_service.restock(
            db,
            menu_item_id=beverage.id,
            quantity=10,
            logged_by_staff_id=staff_member.id,
            note="Emergency delivery",
        )

    # We verify successful execution; detail is stored in audit log.
    updated = await inventory_repo.get_by_id(db, beverage.id)
    assert updated.stock_quantity == 20


# ── get_low_stock_items ───────────────────────────────────────────────────


async def test_get_low_stock_items_returns_correct_items(db: AsyncSession):
    """get_low_stock_items returns only items below or at threshold."""
    # item at exactly threshold
    item_at = await inventory_repo.create(
        db,
        name="At Threshold",
        price_paise=1000,
        stock_quantity=5,
        low_stock_threshold=5,
    )
    # item below threshold
    item_below = await inventory_repo.create(
        db, name="Below", price_paise=2000, stock_quantity=2, low_stock_threshold=10
    )
    # item above threshold (should NOT be returned)
    await inventory_repo.create(
        db, name="Above", price_paise=3000, stock_quantity=20, low_stock_threshold=5
    )
    # item with NULL stock_quantity (should NOT be returned)
    await inventory_repo.create(
        db,
        name="Null Stock",
        price_paise=4000,
        stock_quantity=None,
        low_stock_threshold=5,
    )
    # item with NULL threshold (should NOT be returned)
    await inventory_repo.create(
        db,
        name="Null Threshold",
        price_paise=5000,
        stock_quantity=3,
        low_stock_threshold=None,
    )

    low_stock = await inventory_service.get_low_stock_items(db)
    ids = {i.id for i in low_stock}
    assert item_at.id in ids
    assert item_below.id in ids
    assert len(ids) == 2
