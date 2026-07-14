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
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models.staff import Staff
from backend.schemas.seat import SeatResponse
from backend.services import (
    remote_command_service,
    seat_service,
    tuya_service,
    wol_service,
)

router = APIRouter(prefix="/seats", tags=["seats"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class _MaintenanceBody(BaseModel):
    """Request body for PATCH /seats/{id}/maintenance."""

    note: str | None = None


class _MessageBody(BaseModel):
    """Request body for POST /seats/{id}/message."""

    message: str = Field(..., max_length=1000)


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


@router.post("/{seat_id}/wol", response_model=SeatResponse)
async def trigger_wol(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> SeatResponse:
    """Send a Wake-on-LAN magic packet to a seat (admin only)."""
    return await wol_service.send_wol_to_seat(db, seat_id, staff)


@router.post("/{seat_id}/wol/override", response_model=SeatResponse)
async def wol_override(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> SeatResponse:
    """Manually mark a seat as online, bypassing the WoL watchdog (admin only)."""
    return await wol_service.override_seat_online(db, seat_id, staff)


@router.post("/{seat_id}/message", status_code=status.HTTP_204_NO_CONTENT)
async def send_seat_message(
    seat_id: str,
    body: _MessageBody,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> None:
    """Send a ``SHOW_MESSAGE`` command to the seat's agent (cashier+)."""
    await remote_command_service.send_message(db, seat_id, body.message, staff)


@router.get("/{seat_id}/screenshot")
async def request_seat_screenshot(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Response:
    """Request a screenshot from the seat's agent (cashier+). Returns JPEG bytes."""
    data = await remote_command_service.request_screenshot(db, seat_id, staff)
    return Response(content=data, media_type="image/jpeg")


@router.post("/{seat_id}/restart", status_code=status.HTTP_204_NO_CONTENT)
async def restart_seat(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> None:
    """Send ``RESTART`` to the seat's agent (admin only)."""
    await remote_command_service.restart_seat(db, seat_id, staff)


@router.post("/{seat_id}/shutdown", status_code=status.HTTP_204_NO_CONTENT)
async def shutdown_seat(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> None:
    """Send ``SHUTDOWN`` to the seat's agent (admin only)."""
    await remote_command_service.shutdown_seat(db, seat_id, staff)


@router.post(
    "/{seat_id}/power-on",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_feature("enable_tuya"))],
)
async def power_on_seat(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> None:
    """Power a seat's console ON via its Tuya smart plug (admin only)."""
    await tuya_service.power_on(db, seat_id)


@router.post(
    "/{seat_id}/power-off",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_feature("enable_tuya"))],
)
async def power_off_seat(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> None:
    """Power a seat's console OFF via its Tuya smart plug (admin only)."""
    await tuya_service.power_off(db, seat_id)
