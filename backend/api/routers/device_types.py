"""Device Type management API router — admin-gated.

Routes::

    POST   /api/device-types           → create device type (Admin)
    GET    /api/device-types           → list all device types (Admin)
    GET    /api/device-types/{id}      → get one device type (Admin)
    PUT    /api/device-types/{id}      → update device type (Admin)
    DELETE /api/device-types/{id}      → delete device type (Admin)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.device_type import DeviceType
from backend.models.staff import Staff
from backend.schemas.device_type import (
    DeviceTypeCreate,
    DeviceTypeResponse,
    DeviceTypeUpdate,
)
from backend.services.device_type_service import DeviceTypeService

router = APIRouter(prefix="/device-types", tags=["device-types"])


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """SQLite may strip tzinfo; re-attach UTC so AwareDatetime validates.

    Mirrors ``auth_service._ensure_tz``.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _to_response(dt: DeviceType) -> DeviceTypeResponse:
    """Normalise updated_at/created_at tz and build a DeviceTypeResponse."""
    dt.updated_at = _ensure_tz(dt.updated_at)  # type: ignore[assignment]
    dt.created_at = _ensure_tz(dt.created_at)  # type: ignore[assignment]
    return DeviceTypeResponse.model_validate(dt)


@router.post(
    "",
    response_model=DeviceTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a device type",
)
async def create_device_type(
    body: Annotated[DeviceTypeCreate, Body(description="New device type details")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> DeviceTypeResponse:
    """Create a new device type. Admin only."""
    created = await DeviceTypeService.create(
        db,
        name=body.name,
        description=body.description,
    )
    return _to_response(created)


@router.get(
    "",
    response_model=list[DeviceTypeResponse],
    summary="List all device types",
)
async def list_device_types(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> list[DeviceTypeResponse]:
    """List all device types. Admin only."""
    device_types = await DeviceTypeService.list(db)
    return [_to_response(dt) for dt in device_types]


@router.get(
    "/{device_type_id}",
    response_model=DeviceTypeResponse,
    summary="Get a device type by ID",
)
async def get_device_type(
    device_type_id: Annotated[str, Path(..., description="Device Type ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> DeviceTypeResponse:
    """Get a device type by ID. Admin only."""
    dt = await DeviceTypeService.get_by_id(db, device_type_id)
    if dt is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Device type not found")
    return _to_response(dt)


@router.put(
    "/{device_type_id}",
    response_model=DeviceTypeResponse,
    summary="Update a device type",
)
async def update_device_type(
    device_type_id: Annotated[str, Path(..., description="Device Type ID")],
    body: Annotated[DeviceTypeUpdate, Body(description="Device type fields to update")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> DeviceTypeResponse:
    """Update a device type (PATCH semantics — all fields optional). Admin only."""
    dt = await DeviceTypeService.get_by_id(db, device_type_id)
    if dt is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Device type not found")

    # Apply only fields that were provided (exclude_unset = PATCH semantics)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dt, field, value)

    updated = await DeviceTypeService.update(db, dt)
    return _to_response(updated)


@router.delete(
    "/{device_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a device type",
)
async def delete_device_type(
    device_type_id: Annotated[str, Path(..., description="Device Type ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> Response:
    """Delete a device type. Admin only. Returns 204 on success, 404 if not found."""
    ok = await DeviceTypeService.delete(db, device_type_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Device type not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
