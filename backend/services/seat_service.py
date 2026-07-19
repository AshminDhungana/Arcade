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
from backend.repositories import seat_repo, zone_repo
from backend.schemas.seat import SeatResponse
from backend.services import audit_service


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


async def _seat_to_response(
    db: AsyncSession,
    seat: Seat,
    zone_name_map: dict[str, str] | None = None,
) -> SeatResponse:
    seat.created_at = _ensure_tz(seat.created_at)  # type: ignore[assignment]
    seat.updated_at = _ensure_tz(seat.updated_at)  # type: ignore[assignment]
    resp = SeatResponse.model_validate(seat)
    if seat.zone_id is not None:
        if zone_name_map is not None:
            resp.zone_name = zone_name_map.get(seat.zone_id)
        else:
            zone = await zone_repo.get_by_id(db, seat.zone_id)
            resp.zone_name = zone.name if zone is not None else None
    return resp


async def _broadcast_seat_update(db: AsyncSession, seat: Seat) -> None:
    """Broadcast a ``seat_updated`` event to all connected dashboards."""
    payload = (await _seat_to_response(db, seat)).model_dump(mode="json")
    await ws_manager.broadcast_to_dashboards("seat_updated", payload)


async def set_overlay_forced(
    db: AsyncSession, seat_id: str, value: bool
) -> SeatResponse:
    """Set a seat's ``overlay_forced`` flag and broadcast the change.

    Used by the force-overlay command and by the self-correcting clears on
    session start (HIDE_OVERLAY) and staff override.
    """
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise SeatNotFoundError(seat_id)
    seat.overlay_forced = value
    db.add(seat)
    await db.commit()
    await db.refresh(seat)
    await _broadcast_seat_update(db, seat)
    return await _seat_to_response(db, seat)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def list_seats(db: AsyncSession) -> Sequence[SeatResponse]:
    """Return all seats with their current status and active-session assigned_end_at."""
    seats = await seat_repo.list(db)
    seat_ids = [s.id for s in seats]
    assigned = await seat_repo.assigned_end_at_by_seat(db, seat_ids)
    active = await seat_repo.active_session_by_seat(db, seat_ids)
    zones = await zone_repo.list(db)
    zone_name_map = {z.id: z.name for z in zones}
    responses = []
    for seat in seats:
        resp = await _seat_to_response(db, seat, zone_name_map)
        resp.assigned_end_at = _ensure_tz(assigned.get(seat.id))
        sess = active.get(seat.id)
        if sess is not None:
            resp.current_session_id = sess[0]
            resp.current_session_started_at = _ensure_tz(sess[1])
        responses.append(resp)
    return responses


async def get_seat(db: AsyncSession, seat_id: str) -> SeatResponse:
    """Return a single seat.  Raises 404 if not found."""
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise SeatNotFoundError(seat_id)
    resp = await _seat_to_response(db, seat)
    assigned = await seat_repo.assigned_end_at_by_seat(db, [seat.id])
    resp.assigned_end_at = _ensure_tz(assigned.get(seat.id))
    return resp


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

    await audit_service.log(
        db,
        action=AuditAction.SEAT_MAINTENANCE_ON,
        entity_type="seat",
        entity_id=updated.id,
        staff_id=staff.id if staff else None,
        detail=note or "",
    )

    await _broadcast_seat_update(db, updated)

    return await _seat_to_response(db, updated)


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

    await audit_service.log(
        db,
        action=AuditAction.SEAT_MAINTENANCE_OFF,
        entity_type="seat",
        entity_id=updated.id,
        staff_id=staff.id if staff else None,
        detail="",
    )

    await _broadcast_seat_update(db, updated)

    return await _seat_to_response(db, updated)


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

    await _broadcast_seat_update(db, updated)

    return await _seat_to_response(db, updated)
