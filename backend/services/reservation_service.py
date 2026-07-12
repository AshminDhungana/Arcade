"""Reservation Service — reservation lifecycle business logic.

All public functions are ``async def`` and accept ``db: AsyncSession`` as
their first parameter.  This module is feature-flagged at the API layer
(see ``backend.api.routers.reservations``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Reservation, ReservationStatus
from backend.models._enums import AuditAction
from backend.repositories import reservation_repo, seat_repo
from backend.services import audit_service


class ReservationNotFoundError(HTTPException):
    """Raised when a reservation lookup fails."""

    def __init__(self, reservation_id: str) -> None:
        msg = f"Reservation {reservation_id} not found"
        super().__init__(status_code=404, detail=msg)


class SeatUnavailableError(HTTPException):
    """Raised when a seat is already reserved in the requested window."""

    def __init__(self, seat_id: str) -> None:
        super().__init__(
            status_code=409,
            detail=f"Seat {seat_id} already reserved for this time window",
        )


def _attach_tz(reservation: Reservation) -> Reservation:
    """SQLite may strip tz from DateTime(timezone=True); re-attach UTC so
    Pydantic's ``AwareDatetime`` validates cleanly."""
    if reservation.reserved_from.tzinfo is None:
        reservation.reserved_from = reservation.reserved_from.replace(tzinfo=UTC)
    if reservation.reserved_until is not None:
        if reservation.reserved_until.tzinfo is None:
            reservation.reserved_until = reservation.reserved_until.replace(tzinfo=UTC)
    if reservation.created_at.tzinfo is None:
        reservation.created_at = reservation.created_at.replace(tzinfo=UTC)
    if reservation.updated_at.tzinfo is None:
        reservation.updated_at = reservation.updated_at.replace(tzinfo=UTC)
    return reservation


async def create_reservation(
    db: AsyncSession,
    *,
    seat_id: str,
    customer_name: str,
    reserved_from: datetime,
    reserved_until: datetime | None,
    notes: str | None,
    created_by_staff_id: str,
    member_id: str | None = None,
    group_reservation_id: str | None = None,
    status: ReservationStatus = ReservationStatus.PENDING,
) -> Reservation:
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found")
    conflicting = await reservation_repo.find_conflicting(
        db, seat_id=seat_id, reserved_from=reserved_from, reserved_until=reserved_until
    )
    if conflicting:
        raise SeatUnavailableError(seat_id)
    reservation = await reservation_repo.create(
        db,
        seat_id=seat_id,
        customer_name=customer_name,
        reserved_from=reserved_from,
        reserved_until=reserved_until,
        member_id=member_id,
        group_reservation_id=group_reservation_id,
        notes=notes,
        status=status,
        created_by_staff_id=created_by_staff_id,
    )
    await audit_service.log(
        db,
        action=AuditAction.RESERVATION_CREATED,
        entity_type="reservation",
        entity_id=reservation.id,
        staff_id=created_by_staff_id,
        detail=f"seat_id={seat_id}; customer={customer_name}",
    )
    # flush-only; request-scoped get_db() commits on success
    await db.flush()
    await db.refresh(reservation)
    return _attach_tz(reservation)
