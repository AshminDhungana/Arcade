"""Unit tests for the checkout flow in billing_service (Feature 3.1.2)."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import SeatStatus, SessionStatus
from backend.models._enums import PaymentMethod, PricingModel
from backend.repositories import seat_repo, session_repo, zone_repo
from backend.services.billing_service import (
    checkout_session,
)


@pytest.fixture(autouse=True)
def _mock_print_enqueue():
    """Mock enqueue_and_track_print so the async background task is a no-op."""
    with patch(
        "backend.services.print_service.enqueue_and_track_print", new_callable=AsyncMock
    ) as m:
        yield m


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB.

    Using a file-based DB instead of in-memory avoids aiosqlite threading issues
    during test cleanup (Windows fatal exception on engine.dispose()).
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


async def _create_active_session(db: AsyncSession, duration_minutes: int = 30):
    """Helper to create zone, seat, active session."""
    zone = await zone_repo.create(
        db,
        name="TestZone",
        rate_per_minute_paise=100,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    sess = await session_repo.create(
        db,
        seat_id=seat.id,
        started_at=datetime.now(UTC) - timedelta(minutes=duration_minutes),
        locked_rate_paise=100,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    return sess, seat, zone


# ------------------------------------------------------------------
# checkout_session
# ------------------------------------------------------------------


async def test_checkout_completes_session(db: AsyncSession) -> None:
    """Checkout marks session COMPLETED and seat AVAILABLE."""
    sess, seat, _ = await _create_active_session(db, duration_minutes=10)
    invoice = await checkout_session(db, sess.id, PaymentMethod.CASH)

    assert invoice is not None
    assert invoice.total_paise > 0  # at least 10 minutes charged
    assert invoice.payment_method == PaymentMethod.CASH

    # Refresh session
    updated = await session_repo.get_by_id(db, sess.id)
    assert updated
    assert updated.status == SessionStatus.COMPLETED
    assert updated.ended_at is not None

    # Seat is now AVAILABLE
    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed
    assert refreshed.status == SeatStatus.AVAILABLE


async def test_checkout_respects_pause(db: AsyncSession) -> None:
    """Paused time is excluded from billing."""
    from backend.services import billing_service

    zone = await zone_repo.create(
        db,
        name="TestZone",
        rate_per_minute_paise=100,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    seat = await seat_repo.create(db, name="PC-02", zone_id=zone.id)
    sess = await session_repo.create(
        db,
        seat_id=seat.id,
        started_at=datetime.now(UTC) - timedelta(minutes=10),
        locked_rate_paise=100,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )

    # Manually override elapsed to simulate paused session
    original = billing_service._compute_elapsed_seconds

    def _mock_compute(s):
        return 5 * 60

    billing_service._compute_elapsed_seconds = _mock_compute  # type: ignore[attr-defined]
    try:
        invoice = await checkout_session(db, sess.id, PaymentMethod.CASH)
    finally:
        billing_service._compute_elapsed_seconds = original  # type: ignore[attr-defined]

    # Should charge for 5 minutes, not 10
    assert invoice.total_paise == 5 * 100  # 5 min * 100 paise/min


async def test_checkout_with_pos_items_and_discount(db: AsyncSession) -> None:
    """Checkout sums POS items and applies discount, creating line items for them."""
    from backend.models._enums import InvoiceLineItemType
    from backend.repositories import inventory_repo, pos_repo

    # Create session
    sess, seat, _ = await _create_active_session(db, duration_minutes=10)

    # Set general discount on session
    sess.discount_paise = 200
    await session_repo.update(db, sess)

    # Create menu item
    menu_item = await inventory_repo.create(
        db,
        name="Cold Coke",
        price_paise=150,
        stock_quantity=10,
    )

    # Add POS item to session
    await pos_repo.create(
        db,
        session_id=sess.id,
        menu_item_id=menu_item.id,
        quantity=2,
        unit_price_paise=150,
    )

    invoice = await checkout_session(db, sess.id, PaymentMethod.CASH)

    assert invoice is not None
    assert invoice.discount_paise == 200
    assert invoice.pos_total_paise == 300  # 2 * 150
    # duration 10 mins * rate 100 paise/min = 1000 time charge
    # total = 1000 (time charge) + 300 (POS) - 200 (discount) = 1100
    assert invoice.total_paise == 1100

    # Verify line items
    assert len(invoice.line_items) == 3  # Time charge, POS item, Discount
    pos_li = [
        li for li in invoice.line_items if li.type == InvoiceLineItemType.POS_ITEM
    ]
    discount_li = [
        li for li in invoice.line_items if li.type == InvoiceLineItemType.DISCOUNT
    ]
    time_li = [
        li for li in invoice.line_items if li.type == InvoiceLineItemType.TIME_CHARGE
    ]

    assert len(pos_li) == 1
    assert pos_li[0].description == "Cold Coke"
    assert pos_li[0].quantity == 2
    assert pos_li[0].unit_price_paise == 150
    assert pos_li[0].total_paise == 300

    assert len(discount_li) == 1
    assert discount_li[0].description == "Session discount"
    assert discount_li[0].quantity == 1
    assert discount_li[0].unit_price_paise == 200
    assert discount_li[0].total_paise == 200

    assert len(time_li) == 1


async def test_checkout_missing_session_raises_404(db: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await checkout_session(db, "nonexistent-id", PaymentMethod.CASH)
    assert exc_info.value.status_code == 404


async def test_checkout_already_completed_raises_409(db: AsyncSession) -> None:
    sess, _, _ = await _create_active_session(db, duration_minutes=5)
    # First checkout succeeds
    await checkout_session(db, sess.id, PaymentMethod.CASH)
    # Second checkout fails
    with pytest.raises(HTTPException) as exc_info:
        await checkout_session(db, sess.id, PaymentMethod.CASH)
    assert exc_info.value.status_code == 409


async def test_checkout_enqueues_tracked_print(
    db: AsyncSession, _mock_print_enqueue: AsyncMock
) -> None:
    """Checkout dispatches a tracked print with the invoice id as first arg."""
    session = await _create_active_session(db, duration_minutes=30)
    result = await checkout_session(db, session[0].id, PaymentMethod.CASH)
    # The background task is scheduled via asyncio.create_task; give the loop
    # a chance to run it so the mock is awaited before we assert.
    await asyncio.sleep(0)
    _mock_print_enqueue.assert_awaited_once()
    args, _kwargs = _mock_print_enqueue.call_args
    assert args[0] == result.id  # invoice_id is the first positional arg
