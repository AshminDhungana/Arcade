"""Reservation API router.

Feature-flagged by ``enable_reservations``.  All endpoints require a
Cashier (or Admin) token.  The server is the source of truth for
``created_by_staff_id`` — it is taken from the authenticated staff, not
the request body.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models._enums import ReservationStatus
from backend.models.staff import Staff
from backend.schemas.reservation import (
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)
from backend.services import reservation_service

router = APIRouter(prefix="/reservations", tags=["reservations"])
router.dependencies.append(Depends(require_feature("enable_reservations")))

DbDep = Annotated[AsyncSession, Depends(get_db)]
CashierDep = Annotated[Staff, Depends(require_cashier)]


@router.get("", response_model=list[ReservationResponse])
async def list_reservations(
    db: DbDep,
    staff: CashierDep,
    seat_id: str | None = None,
    member_id: str | None = None,
    reservation_status: ReservationStatus | None = None,
) -> list[ReservationResponse]:
    reservations = await reservation_service.list_reservations(
        db, seat_id=seat_id, member_id=member_id, status=reservation_status
    )
    return [ReservationResponse.model_validate(r) for r in reservations]


@router.post(
    "",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    body: ReservationCreate, db: DbDep, staff: CashierDep
) -> ReservationResponse:
    reservation = await reservation_service.create_reservation(
        db,
        seat_id=body.seat_id,
        customer_name=body.customer_name,
        reserved_from=body.reserved_from,
        reserved_until=body.reserved_until,
        notes=body.notes,
        created_by_staff_id=staff.id,
        member_id=body.member_id,
        group_reservation_id=body.group_reservation_id,
        status=body.status,
    )
    return ReservationResponse.model_validate(reservation)


@router.patch("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: str, body: ReservationUpdate, db: DbDep, staff: CashierDep
) -> ReservationResponse:
    if body.status is not None:
        if body.status == ReservationStatus.CONFIRMED:
            reservation = await reservation_service.confirm_reservation(
                db, reservation_id=reservation_id, staff_id=staff.id
            )
        elif body.status == ReservationStatus.CANCELLED:
            reservation = await reservation_service.cancel_reservation(
                db, reservation_id=reservation_id, staff_id=staff.id
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only CONFIRMED or CANCELLED status transitions "
                    "are allowed via PATCH"
                ),
            )
    else:
        reservation = await reservation_service.update_reservation(
            db, reservation_id=reservation_id, updates=body, staff_id=staff.id
        )
    return ReservationResponse.model_validate(reservation)


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(reservation_id: str, db: DbDep, staff: CashierDep) -> None:
    await reservation_service.delete_reservation(db, reservation_id=reservation_id)
