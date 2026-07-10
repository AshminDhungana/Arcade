"""Staff management API router.

Routes::

    POST   /api/staff                 → create staff (Admin)
    PATCH  /api/staff/{id}/pin        → update PIN (Admin or self)
    PATCH  /api/staff/{id}/deactivate → deactivate staff (Admin)
    GET    /api/staff                 → list all staff (Admin)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_self_or_admin
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.schemas.staff import StaffCreate, StaffPinUpdate, StaffResponse
from backend.services.staff_service import StaffService

router = APIRouter(prefix="/staff", tags=["staff"])


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """SQLite may strip tzinfo; re-attach UTC so AwareDatetime validates.

    Mirrors ``auth_service._ensure_tz``.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _to_response(staff) -> StaffResponse:  # type: ignore[no-untyped-def]
    """Normalise ``updated_at`` timezone and build a ``StaffResponse``."""
    staff.updated_at = _ensure_tz(staff.updated_at)
    return StaffResponse.model_validate(staff)


@router.post(
    "",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff member",
)
async def create_staff(
    body: Annotated[StaffCreate, Body(description="New staff details")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> StaffResponse:
    """Create a new staff member. Admin only.

    The PIN is hashed with Argon2id and the new staff starts at
    ``token_version=0``.
    """
    created = await StaffService.create(
        db,
        name=body.name,
        role=body.role,
        pin=body.pin,
        is_active=body.is_active,
        staff=staff,
    )
    return _to_response(created)


@router.patch(
    "/{staff_id}/pin",
    response_model=StaffResponse,
    summary="Update a staff member's PIN",
)
async def update_staff_pin(
    staff_id: Annotated[str, Path(..., description="Target staff ID")],
    body: Annotated[StaffPinUpdate, Body(description="New PIN")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_self_or_admin)] = None,  # noqa: B008
) -> StaffResponse:
    """Update the PIN for a staff member. Admin or the staff member themselves.

    Increments ``token_version`` to invalidate all existing JWTs.
    """
    updated = await StaffService.update_pin(
        db, staff_id=staff_id, new_pin=body.pin, staff=staff
    )
    return _to_response(updated)


@router.patch(
    "/{staff_id}/deactivate",
    response_model=StaffResponse,
    summary="Deactivate a staff member",
)
async def deactivate_staff(
    staff_id: Annotated[str, Path(..., description="Target staff ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> StaffResponse:
    """Deactivate a staff member. Admin only.

    Sets ``is_active=False`` and increments ``token_version`` to invalidate
    all existing JWTs.
    """
    updated = await StaffService.deactivate(db, staff_id=staff_id, staff=staff)
    return _to_response(updated)


@router.get(
    "",
    response_model=list[StaffResponse],
    summary="List all staff",
)
async def list_staff(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> list[StaffResponse]:
    """List all staff members. Admin only."""
    staff_list = await StaffService.list_staff(db)
    return [_to_response(s) for s in staff_list]
