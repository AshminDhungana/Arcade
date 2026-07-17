"""Unit tests for :mod:`backend.services.shift_service` (open + current)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.feature_flags import _flag_cache
from backend.models._enums import (
    AuditAction,
    InvoicePrintStatus,
    PaymentMethod,
    PricingModel,
    ShiftStatus,
)
from backend.repositories import audit_repo, invoice_repo, session_repo, shift_repo
from backend.services.shift_service import (
    close_shift,
    get_current_shift,
    get_shift_report,
    open_shift,
)


@pytest.fixture(autouse=True)
async def _reset_gate_flag() -> AsyncGenerator[None]:
    """Isolate the in-memory flag cache between tests."""
    _flag_cache.pop("block_shift_close_unprinted", None)
    yield
    _flag_cache.pop("block_shift_close_unprinted", None)


def _enable_gate() -> None:
    _flag_cache["block_shift_close_unprinted"] = True


async def _make_failed_invoice(db, shift_id: str):
    """Create a session + a FAILED invoice stamped to *shift_id*."""
    sess = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift_id,
    )
    inv = await invoice_repo.create(
        db,
        session_id=sess.id,
        shift_id=shift_id,
        payment_method=PaymentMethod.CASH,
        total_paise=1000,
    )
    inv.print_status = InvoicePrintStatus.FAILED
    await invoice_repo.update(db, inv)
    return inv


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_open_shift_creates_open_record(db: AsyncSession) -> None:
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    assert shift.status == ShiftStatus.OPEN
    assert shift.float_paise == 5000
    assert shift.opened_by_staff_id == "staff-1"
    assert shift.opened_at is not None


async def test_open_shift_rejects_when_one_already_open(db: AsyncSession) -> None:
    await open_shift(db, staff_id="staff-1", opening_cash_paise=1000)
    with pytest.raises(HTTPException) as exc:
        await open_shift(db, staff_id="staff-2", opening_cash_paise=2000)
    assert exc.value.status_code == 409
    assert "SHIFT_ALREADY_OPEN" in exc.value.detail


async def test_get_current_shift_returns_open(db: AsyncSession) -> None:
    opened = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    current = await get_current_shift(db)
    assert current is not None
    assert current.id == opened.id


async def test_get_current_shift_none_when_closed(db: AsyncSession) -> None:
    opened = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    opened.status = ShiftStatus.CLOSED
    opened.closed_at = datetime.now(UTC)
    await shift_repo.update(db, opened)
    assert await get_current_shift(db) is None


async def test_close_shift_sets_closed_state(db: AsyncSession) -> None:
    await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    closed = await close_shift(db, staff_id="staff-1", closing_cash_paise=6500)
    assert closed.status == ShiftStatus.CLOSED
    assert closed.closed_by_staff_id == "staff-1"
    assert closed.counted_paise == 6500
    assert closed.closed_at is not None


async def test_close_shift_rejects_when_none_open(db: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc:
        await close_shift(db, staff_id="staff-1", closing_cash_paise=0)
    assert exc.value.status_code == 409
    assert "NO_OPEN_SHIFT" in exc.value.detail


async def test_get_shift_report_reconciliation(db: AsyncSession) -> None:
    """AC-10: expected cash = float + cash collected; variance = counted - expected."""
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)

    sess = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )
    # CASH invoice 1500 total, 300 POS; CARD invoice 1000 total
    await invoice_repo.create(
        db,
        session_id=sess.id,
        shift_id=shift.id,
        payment_method=PaymentMethod.CASH,
        total_paise=1500,
        pos_total_paise=300,
    )
    await invoice_repo.create(
        db,
        session_id=sess.id,
        shift_id=shift.id,
        payment_method=PaymentMethod.CARD,
        total_paise=1000,
        pos_total_paise=200,
    )
    # A second session on the same shift (no invoice)
    await session_repo.create(
        db,
        seat_id="seat-2",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )

    report = await get_shift_report(db, shift_id=shift.id)
    assert report.session_count == 2
    assert report.invoice_count == 2
    assert report.cash_collected_paise == 1500
    assert report.total_revenue_paise == 2500
    assert report.pos_total_paise == 500
    # expected = float(5000) + cash collected(1500) = 6500
    assert report.expected_cash_paise == 6500
    # variance None while shift still open (counted_paise undecided)
    assert report.variance_paise is None


async def test_get_shift_report_variance_when_closed(db: AsyncSession) -> None:
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    sess = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )
    await invoice_repo.create(
        db,
        session_id=sess.id,
        shift_id=shift.id,
        payment_method=PaymentMethod.CASH,
        total_paise=1500,
    )
    await close_shift(db, staff_id="staff-1", closing_cash_paise=6400)
    report = await get_shift_report(db, shift_id=shift.id)
    # expected = 5000 + 1500 = 6500; counted = 6400 -> variance = -100 (short)
    assert report.expected_cash_paise == 6500
    assert report.variance_paise == -100


async def test_get_shift_report_not_found(db: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc:
        await get_shift_report(db, shift_id="missing")
    assert exc.value.status_code == 404


def test_shift_close_unprinted_audit_action_defined() -> None:
    """The new audit action exists with the expected stored value."""
    from backend.models._enums import AuditAction

    assert AuditAction.SHIFT_CLOSE_UNPRINTED.value == "SHIFT_CLOSE_UNPRINTED"


def test_block_shift_close_flag_seeded_false() -> None:
    """The new gate flag ships default-off (non-blocking) in the seed set."""
    from backend.scripts.seed_dev import DEFAULT_FEATURE_FLAGS

    assert "block_shift_close_unprinted" in DEFAULT_FEATURE_FLAGS
    assert DEFAULT_FEATURE_FLAGS["block_shift_close_unprinted"] == "false"


async def test_close_shift_warns_when_unprinted_and_flag_off(db: AsyncSession) -> None:
    """Default (flag off): shift still closes, but a warning audit is logged."""
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    await _make_failed_invoice(db, shift.id)

    closed = await close_shift(db, staff_id="staff-1", closing_cash_paise=5000)

    assert closed.status == ShiftStatus.CLOSED
    logs = await audit_repo.list(db, action=AuditAction.SHIFT_CLOSE_UNPRINTED.value)
    assert len(logs) == 1
    assert "unprinted_count=1" in (logs[0].detail or "")


async def test_close_shift_no_warning_when_all_printed(db: AsyncSession) -> None:
    """No unprinted invoices -> no SHIFT_CLOSE_UNPRINTED audit is written."""
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    sess = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=shift.id,
    )
    await invoice_repo.create(
        db,
        session_id=sess.id,
        shift_id=shift.id,
        payment_method=PaymentMethod.CASH,
        total_paise=1000,
    )

    await close_shift(db, staff_id="staff-1", closing_cash_paise=5000)

    logs = await audit_repo.list(db, action=AuditAction.SHIFT_CLOSE_UNPRINTED.value)
    assert len(logs) == 0
