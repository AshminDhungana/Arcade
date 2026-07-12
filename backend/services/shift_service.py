"""Shift Service — shift lifecycle business logic.

Public functions are ``async def`` and accept ``db: AsyncSession`` first.
Reconciliation math is integer-only in paise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Shift
from backend.models._enums import AuditAction, PaymentMethod, ShiftStatus
from backend.repositories import invoice_repo, session_repo, shift_repo
from backend.schemas.shift import ShiftReportResponse, ShiftResponse
from backend.services import audit_service


async def open_shift(
    db: AsyncSession, *, staff_id: str, opening_cash_paise: int = 0
) -> Shift:
    """Open a new shift.

    Rejects (409) if a shift is already OPEN. Creates the ``Shift`` record
    and audits ``SHIFT_OPEN``.
    """
    existing = await shift_repo.get_open_shift(db)
    if existing:
        raise HTTPException(status_code=409, detail="SHIFT_ALREADY_OPEN")

    shift = await shift_repo.create(
        db,
        opened_by_staff_id=staff_id,
        opened_at=datetime.now(UTC),
        float_paise=opening_cash_paise,
        status=ShiftStatus.OPEN,
    )
    await audit_service.log(
        db,
        action=AuditAction.SHIFT_OPEN,
        entity_type="shift",
        entity_id=shift.id,
        staff_id=staff_id,
        detail=f"float_paise={opening_cash_paise}",
    )
    return shift


async def get_current_shift(db: AsyncSession) -> Shift | None:
    """Return the currently OPEN shift, or ``None``."""
    return await shift_repo.get_open_shift(db)


async def close_shift(
    db: AsyncSession, *, staff_id: str, closing_cash_paise: int
) -> Shift:
    """Close the currently OPEN shift.

    Rejects (409) if no shift is open. Sets ``closed_by_staff_id``,
    ``counted_paise`` (closing cash), ``closed_at``, and ``status=CLOSED``,
    then audits ``SHIFT_CLOSE``.
    """
    shift = await shift_repo.get_open_shift(db)
    if shift is None:
        raise HTTPException(status_code=409, detail="NO_OPEN_SHIFT")

    shift.closed_by_staff_id = staff_id
    shift.counted_paise = closing_cash_paise
    shift.closed_at = datetime.now(UTC)
    shift.status = ShiftStatus.CLOSED
    shift = await shift_repo.update(db, shift)

    await audit_service.log(
        db,
        action=AuditAction.SHIFT_CLOSE,
        entity_type="shift",
        entity_id=shift.id,
        staff_id=staff_id,
        detail=f"counted_paise={closing_cash_paise}",
    )
    return shift


@dataclass(frozen=True)
class ShiftReport:
    shift: Shift
    session_count: int
    invoice_count: int
    total_revenue_paise: int
    pos_total_paise: int
    cash_collected_paise: int
    expected_cash_paise: int
    variance_paise: int | None


async def get_shift_report(db: AsyncSession, *, shift_id: str) -> ShiftReportResponse:
    """Build a cash-reconciliation report for *shift_id*.

    expected_cash = float_paise + sum(invoice.total_paise where
    payment_method == CASH). variance = counted_paise - expected_cash
    (``None`` while the shift is still open).
    """
    shift = await shift_repo.get_by_id(db, shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")

    sessions = await session_repo.list_by_shift(db, shift_id)
    invoices = await invoice_repo.list_by_shift(db, shift_id)

    cash_collected_paise = sum(
        i.total_paise for i in invoices if i.payment_method == PaymentMethod.CASH
    )
    total_revenue_paise = sum(i.total_paise for i in invoices)
    pos_total_paise = sum(i.pos_total_paise for i in invoices)
    expected_cash_paise = shift.float_paise + cash_collected_paise
    variance_paise = (
        shift.counted_paise - expected_cash_paise
        if shift.counted_paise is not None
        else None
    )

    # SQLite strips tzinfo from DateTime columns on round-trip; re-attach UTC
    # before building the response (which requires timezone-aware datetimes).
    if shift.opened_at.tzinfo is None:
        shift.opened_at = shift.opened_at.replace(tzinfo=UTC)
    if shift.closed_at is not None and shift.closed_at.tzinfo is None:
        shift.closed_at = shift.closed_at.replace(tzinfo=UTC)

    report = ShiftReport(
        shift=shift,
        session_count=len(sessions),
        invoice_count=len(invoices),
        total_revenue_paise=total_revenue_paise,
        pos_total_paise=pos_total_paise,
        cash_collected_paise=cash_collected_paise,
        expected_cash_paise=expected_cash_paise,
        variance_paise=variance_paise,
    )
    return ShiftReportResponse(
        shift=ShiftResponse.model_validate(report.shift),
        session_count=report.session_count,
        invoice_count=report.invoice_count,
        total_revenue_paise=report.total_revenue_paise,
        pos_total_paise=report.pos_total_paise,
        cash_collected_paise=report.cash_collected_paise,
        expected_cash_paise=report.expected_cash_paise,
        variance_paise=report.variance_paise,
    )
