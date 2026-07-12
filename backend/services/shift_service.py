"""Shift Service — shift lifecycle business logic.

Public functions are ``async def`` and accept ``db: AsyncSession`` first.
Reconciliation math is integer-only in paise.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Shift
from backend.models._enums import AuditAction, ShiftStatus
from backend.repositories import shift_repo
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
