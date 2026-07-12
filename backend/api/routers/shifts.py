"""Shift API router — open/close/current/report endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.schemas.shift import (
    ShiftCloseRequest,
    ShiftOpenRequest,
    ShiftReportResponse,
    ShiftResponse,
)
from backend.services import shift_service

router = APIRouter(prefix="/shifts", tags=["shifts"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
CashierDep = Annotated[Staff, Depends(require_cashier)]
AdminDep = Annotated[Staff, Depends(require_admin)]


@router.post("/open", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def open_shift(
    body: ShiftOpenRequest, db: DbDep, staff: CashierDep
) -> ShiftResponse:
    shift = await shift_service.open_shift(
        db, staff_id=staff.id, opening_cash_paise=body.float_paise
    )
    return ShiftResponse.model_validate(shift)


@router.post("/close", response_model=ShiftResponse)
async def close_shift(
    body: ShiftCloseRequest, db: DbDep, staff: CashierDep
) -> ShiftResponse:
    shift = await shift_service.close_shift(
        db, staff_id=staff.id, closing_cash_paise=body.counted_paise
    )
    return ShiftResponse.model_validate(shift)


@router.get("/current", response_model=ShiftResponse | None)
async def get_current_shift(db: DbDep, staff: CashierDep) -> ShiftResponse | None:
    shift = await shift_service.get_current_shift(db)
    return ShiftResponse.model_validate(shift) if shift else None


@router.get("/{shift_id}/report", response_model=ShiftReportResponse)
async def get_shift_report(
    shift_id: str, db: DbDep, staff: AdminDep
) -> ShiftReportResponse:
    return await shift_service.get_shift_report(db, shift_id=shift_id)
