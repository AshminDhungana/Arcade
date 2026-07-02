"""Seat Service — business logic for seat management.

All public functions are ``async def`` and accept ``db: AsyncSession`` as their
first parameter.  Status changes trigger a WebSocket broadcast to all
dashboard clients via the module-level ``WebSocketManager`` singleton.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ws_manager import manager as ws_manager
from backend.models._enums import AuditAction, SeatStatus
from backend.models.seat import Seat
from backend.models.staff import Staff
from backend.repositories import audit_repo, seat_repo
from backend.schemas.seat import SeatResponse


class SeatNotFoundError(HTTPException):
    """Raised when a seat lookup fails."""

    def __init__(self, seat_id: str) -> None:
        super().__init__(status_code=404, detail=f"Seat {seat_id} not found")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """SQLite sometimes strips timezone info from DateTime(timezone=True).

    Re-attach UTC when it is missing so Pydantic's ``AwareDatetime``
    validates cleanly.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _seat_to_response(seat: Seat) -> SeatResponse:
    seat.created_at = _ensure_tz(seat.created_at)  # type: ignore[assignment]
    seat.updated_at = _ensure_tz(seat.updated_at)  # type: ignore[assignment]
    return SeatResponse.model_validate(seat)


async def _broadcast_seat_update(seat: Seat) -> None:
    """Broadcast a ``seat_updated`` event to all connected dashboards."""
    payload = _seat_to_response(seat).model_dump(mode="json")
    await ws_manager.broadcast_to_dashboards("seat_updated", payload)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_seats(db: AsyncSession) -> Sequence[SeatResponse]:
    """Return all seats with their current status."""
    seats = await seat_repo.list(db)
    return [_seat_to_response(s) for s in seats]


async def get_seat(db: AsyncSession, seat_id: str) -> SeatResponse:
    """Return a single seat.  Raises 404 if not found."""
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise SeatNotFoundError(seat_id)
    return _seat_to_response(seat)


async def set_maintenance(
    db: AsyncSession,
    seat_id: str,
    note: str | None,
    staff: Staff | None,
) -> SeatResponse:
    """Set a seat's status to MAINTENANCE and log an audit entry.
    Args:
        db: Active async SQLAlchemy session.
        seat_id: The seat's UUID.
        note: Optional maintenance note (stored in ``seat.notes``).
        staff: The staff member performing the action.

    Returns:
        The updated seat as a ``SeatResponse``.

    Raises:
        HTTPException(404): If the seat does not exist.
    """
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise SeatNotFoundError(seat_id)

    seat.status = SeatStatus.MAINTENANCE
    seat.notes = note or seat.notes
    updated = await seat_repo.update(db, seat)

    await audit_repo.create(
        db,
        action=AuditAction.SEAT_MAINTENANCE_ON.value,
        entity_type="seat",
        entity_id=updated.id,
        staff_id=staff.id if staff else None,
        detail=note or "",
    )

    await _broadcast_seat_update(updated)

    return _seat_to_response(updated)


async def clear_maintenance(
    db: AsyncSession,
    seat_id: str,
    staff: Staff | None,
) -> SeatResponse:
    """Clear a seat's MAINTENANCE status and set it to AVAILABLE.

    Args:
        db: Active async SQLAlchemy session.
        seat_id: The seat's UUID.
        staff: The staff member performing the action.

    Returns:
        The updated seat as a ``SeatResponse``.

    Raises:
        HTTPException(404): If the seat does not exist.
    """
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise SeatNotFoundError(seat_id)

    seat.status = SeatStatus.AVAILABLE
    seat.notes = None
    updated = await seat_repo.update(db, seat)

    await audit_repo.create(
        db,
        action=AuditAction.SEAT_MAINTENANCE_OFF.value,
        entity_type="seat",
        entity_id=updated.id,
        staff_id=staff.id if staff else None,
        detail="",
    )

    await _broadcast_seat_update(updated)

    return _seat_to_response(updated)


async def update_mac_address(
    db: AsyncSession,
    seat_id: str,
    mac: str | None,
) -> SeatResponse:
    """Update the MAC address for a seat.

    Usually called from the WebSocket REGISTER handler when an agent
    first connects.

    Args:
        db: Active async SQLAlchemy session.
        seat_id: The seat's UUID.
        mac: MAC address string (e.g. ``"aa:bb:cc:dd:ee:ff"``) or ``None``.

    Returns:
        The updated seat as a ``SeatResponse``.

    Raises:
        HTTPException(404): If the seat does not exist.
    """
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise SeatNotFoundError(seat_id)

    seat.mac_address = mac
    updated = await seat_repo.update(db, seat)

    await _broadcast_seat_update(updated)

    return _seat_to_response(updated)
