"""Seat API router.

Routes::

    GET   /api/seats                → list all seats (cashier+)
    GET   /api/seats/{id}           → get a single seat (cashier+)
    PATCH /api/seats/{id}/maintenance  → set maintenance (admin)
    DELETE /api/seats/{id}/maintenance → clear maintenance (admin)
    POST  /api/seats/{id}/wol       → trigger Wake-on-LAN (admin)
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.core.security import hash_pin
from backend.core.ws_manager import manager
from backend.models.seat import Seat
from backend.models.staff import Staff
from backend.repositories import seat_repo
from backend.schemas.seat import SeatResponse
from backend.services import (
    remote_command_service,
    seat_service,
    tuya_service,
    wol_service,
)
from backend.services.enrollment_service import generate_enroll_code

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


class _OverlayBody(BaseModel):
    """Request body for POST /seats/{id}/overlay."""

    show: bool


class _BulkOverlayFailure(BaseModel):
    """One seat that could not be forced (e.g. agent offline)."""

    seat_id: str
    detail: str


class _BulkOverlayResponse(BaseModel):
    """Summary of a bulk force-overlay operation."""

    succeeded: list[str]
    failed: list[_BulkOverlayFailure]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/bulk/overlay", response_model=_BulkOverlayResponse)
async def bulk_seat_overlay(
    body: _OverlayBody,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> _BulkOverlayResponse:
    """Force overlay on/off for all targeted seats (admin only)."""
    result = await remote_command_service.bulk_force_overlay(db, body.show, staff)
    return _BulkOverlayResponse(**result)


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


@router.post("/{seat_id}/overlay", status_code=status.HTTP_204_NO_CONTENT)
async def force_seat_overlay(
    seat_id: str,
    body: _OverlayBody,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> None:
    """Force a seat's kiosk overlay on/off (admin only)."""
    await remote_command_service.force_overlay(db, seat_id, body.show, staff)


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


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------


class _EnrollCodeResponse(BaseModel):
    """Response for POST /seats/{id}/enroll-code."""

    code: str
    expires_at: str


class _OverridePinResponse(BaseModel):
    """Response for POST /seats/{id}/override-pin."""

    override_pin: str


@router.post("/{seat_id}/enroll-code", response_model=_EnrollCodeResponse)
async def create_enroll_code(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> _EnrollCodeResponse:
    """Generate a single-use, 15-minute enroll code for a seat (admin only)."""
    code = await generate_enroll_code(db, seat_id, ttl_seconds=900)
    seat = await db.get(Seat, seat_id)
    expires = seat.enroll_code_expires_at if seat else None
    return _EnrollCodeResponse(
        code=code,
        expires_at=(expires or datetime.now(UTC)).isoformat(),
    )


@router.post("/{seat_id}/override-pin", response_model=_OverridePinResponse)
async def regenerate_override_pin(
    seat_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> _OverridePinResponse:
    """Mint/regenerate a seat's staff-override PIN (admin). Returns the plaintext
    PIN once (it is one-way hashed, never stored plaintext) and pushes the new
    hash to a connected agent via WebSocket.
    """
    pin = f"{secrets.randbelow(1_000_000):06d}"
    pin_hash = hash_pin(pin)
    await seat_repo.set_override_pin_hash(db, seat_id, pin_hash)
    await manager.push_override_pin(seat_id, pin_hash)
    return _OverridePinResponse(override_pin=pin)
