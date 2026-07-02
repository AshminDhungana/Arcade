"""Seat API router.

Routes::

    GET   /api/seats                → list all seats (cashier+)
    GET   /api/seats/{id}           → get a single seat (cashier+)
    PATCH /api/seats/{id}/maintenance  → set maintenance (admin)
    DELETE /api/seats/{id}/maintenance → clear maintenance (admin)
    POST  /api/seats/{id}/wol       → trigger Wake-on-LAN (admin)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.schemas.seat import SeatResponse
from backend.services import seat_service

router = APIRouter(prefix="/seats", tags=["seats"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class _MaintenanceBody(BaseModel):
    """Request body for PATCH /seats/{id}/maintenance."""

    note: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
async def list_seats(
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Sequence[SeatResponse]:
    """List all seats with their current status."""
    return await seat_service.list_seats(db)


@router.get("/{seat_id}")
async def get_seat(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> SeatResponse:
    """Get a single seat by ID."""
    return await seat_service.get_seat(db, seat_id)


@router.patch("/{seat_id}/maintenance", status_code=status.HTTP_200_OK)
async def set_maintenance(
    seat_id: str,
    body: _MaintenanceBody,
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> SeatResponse:
    """Set a seat to MAINTENANCE status (admin only).

    Optionally includes a maintenance note in the request body.
    """
    return await seat_service.set_maintenance(db, seat_id, body.note, staff)


@router.delete("/{seat_id}/maintenance")
async def clear_maintenance(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> SeatResponse:
    """Clear MAINTENANCE status and set seat to AVAILABLE (admin only)."""
    return await seat_service.clear_maintenance(db, seat_id, staff)


@router.post("/{seat_id}/wol", status_code=status.HTTP_202_ACCEPTED)
async def send_wol(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> dict[str, str]:
    """Send a Wake-on-LAN magic packet to a seat (admin only; no-op placeholder)."""
    # TODO: delegate to wol_service when available (Feature 2.1.3)
    seat = await seat_service.get_seat(db, seat_id)
    return {"detail": f"Wake-on-LAN sent to seat {seat.name}", "seat_id": seat_id}
