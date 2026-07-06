"""Unit tests for the checkout flow in billing_service (Feature 3.1.2)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

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


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


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
