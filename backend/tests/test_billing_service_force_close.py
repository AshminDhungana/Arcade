"""Service-layer tests for PIN force-close and held-seat release (isolated DB)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.security import hash_pin
from backend.models import SeatStatus, SessionStatus
from backend.models._enums import (
    AuditAction,
    InvoicePrintStatus,
    PaymentMethod,
    PricingModel,
)
from backend.repositories import (
    audit_repo,
    invoice_repo,
    seat_repo,
    session_repo,
    zone_repo,
)
from backend.services import billing_service


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


async def _held_setup(db: AsyncSession, duration_minutes: int = 10):
    """Create a session in the HELD state: COMPLETED + seat IN_USE + FAILED invoice."""
    zone = await zone_repo.create(
        db,
        name="Z",
        rate_per_minute_paise=100,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    seat = await seat_repo.create(db, name="PC-X", zone_id=zone.id)
    sess = await session_repo.create(
        db,
        seat_id=seat.id,
        started_at=datetime.now(UTC) - timedelta(minutes=duration_minutes),
        locked_rate_paise=100,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    sess.status = SessionStatus.COMPLETED
    sess.ended_at = datetime.now(UTC)
    await session_repo.update(db, sess)
    seat.status = SeatStatus.IN_USE
    await seat_repo.update(db, seat)
    inv = await invoice_repo.create(
        db, session_id=sess.id, payment_method=PaymentMethod.CASH, total_paise=100
    )
    inv.print_status = InvoicePrintStatus.FAILED
    await invoice_repo.update(db, inv)
    return sess, seat, inv


def _staff_with_pin(pin: str) -> SimpleNamespace:
    return SimpleNamespace(id="cashier-1", pin_hash=hash_pin(pin))


async def test_force_close_releases_seat_and_audits(db: AsyncSession) -> None:
    sess, seat, _ = await _held_setup(db)
    staff = _staff_with_pin("1234")
    invoice = await billing_service.force_close_unprinted(
        db, sess.id, "1234", "printer broken", staff
    )
    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.AVAILABLE
    assert invoice.print_status == InvoicePrintStatus.FAILED
    audits = await audit_repo.list(db, entity_id=sess.id)
    assert any(a.action == AuditAction.CHECKOUT_FORCED_UNPRINTED for a in audits)


async def test_force_close_rejects_wrong_pin(db: AsyncSession) -> None:
    sess, seat, _ = await _held_setup(db)
    staff = _staff_with_pin("1234")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await billing_service.force_close_unprinted(db, sess.id, "0000", "x", staff)
    assert exc.value.status_code == 403


async def test_force_close_rejects_already_released(db: AsyncSession) -> None:
    sess, seat, _ = await _held_setup(db)
    seat.status = SeatStatus.AVAILABLE
    await seat_repo.update(db, seat)
    staff = _staff_with_pin("1234")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await billing_service.force_close_unprinted(db, sess.id, "1234", "x", staff)
    assert exc.value.status_code == 409


async def test_reprint_succeeds_releases_held_seat(db: AsyncSession) -> None:
    """When a FAILED invoice is marked PRINTED, a held seat is released."""
    from unittest.mock import patch

    from backend.core.feature_flags import _flag_cache
    from backend.services import billing_service as bs

    _flag_cache["require_print_before_release"] = True
    zone = await zone_repo.create(
        db,
        name="Z",
        rate_per_minute_paise=100,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    seat = await seat_repo.create(db, name="PC-R", zone_id=zone.id)
    sess = await session_repo.create(
        db,
        seat_id=seat.id,
        started_at=datetime.now(UTC) - timedelta(minutes=5),
        locked_rate_paise=100,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    sess.status = SessionStatus.COMPLETED
    sess.ended_at = datetime.now(UTC)
    await session_repo.update(db, sess)
    seat.status = SeatStatus.IN_USE
    await seat_repo.update(db, seat)
    inv = await invoice_repo.create(
        db, session_id=sess.id, payment_method=PaymentMethod.CASH, total_paise=50
    )
    inv.print_status = InvoicePrintStatus.FAILED
    await invoice_repo.update(db, inv)

    config = SimpleNamespace(cafe_name="Test")

    async def _fake_print(invoice_id, response, cafe_name, cfg, **kw):
        i = await invoice_repo.get_by_id(db, invoice_id)
        i.print_status = InvoicePrintStatus.PRINTED
        await invoice_repo.update(db, i)

    with (
        patch("backend.services.billing_service.get_config", return_value=config),
        patch("backend.services.print_service.enqueue_and_track_print", _fake_print),
    ):
        await _fake_print(inv.id, None, "Test", config)
        await bs._maybe_release_held_seat(db, inv)

    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.AVAILABLE
