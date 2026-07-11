"""Zone management API router — admin-gated.

Routes::

    POST   /api/zones          → create zone (Admin)
    GET    /api/zones          → list all zones (Admin)
    GET    /api/zones/{id}     → get one zone (Admin)
    PUT    /api/zones/{id}     → update zone (Admin)
    DELETE /api/zones/{id}     → delete zone (Admin)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.models.zone import Zone
from backend.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate
from backend.services.zone_service import ZoneService

router = APIRouter(prefix="/zones", tags=["zones"])


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """SQLite may strip tzinfo; re-attach UTC so AwareDatetime validates.

    Mirrors ``auth_service._ensure_tz``.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _to_response(zone: Zone) -> ZoneResponse:
    """Normalise ``updated_at``/``created_at`` timezone and build a ``ZoneResponse``."""
    zone.updated_at = _ensure_tz(zone.updated_at)  # type: ignore[assignment]
    zone.created_at = _ensure_tz(zone.created_at)  # type: ignore[assignment]
    return ZoneResponse.model_validate(zone)


@router.post(
    "",
    response_model=ZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a zone",
)
async def create_zone(
    body: Annotated[ZoneCreate, Body(description="New zone details")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> ZoneResponse:
    """Create a new zone. Admin only."""
    created = await ZoneService.create(
        db,
        name=body.name,
        rate_per_minute_paise=body.rate_per_minute_paise,
        rate_per_hour_paise=body.rate_per_hour_paise,
        pricing_model=body.pricing_model,
        block_minutes=body.block_minutes,
    )
    return _to_response(created)


@router.get(
    "",
    response_model=list[ZoneResponse],
    summary="List all zones",
)
async def list_zones(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> list[ZoneResponse]:
    """List all zones. Admin only."""
    zones = await ZoneService.list(db)
    return [_to_response(z) for z in zones]


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Get a zone by ID",
)
async def get_zone(
    zone_id: Annotated[str, Path(..., description="Zone ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> ZoneResponse:
    """Get a zone by ID. Admin only."""
    zone = await ZoneService.get_by_id(db, zone_id)
    if zone is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Zone not found")
    return _to_response(zone)


@router.put(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Update a zone",
)
async def update_zone(
    zone_id: Annotated[str, Path(..., description="Zone ID")],
    body: Annotated[ZoneUpdate, Body(description="Zone fields to update")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> ZoneResponse:
    """Update a zone (PATCH semantics — all fields optional). Admin only."""
    zone = await ZoneService.get_by_id(db, zone_id)
    if zone is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Zone not found")

    # Apply only fields that were provided (exclude_unset = PATCH semantics)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    updated = await ZoneService.update(db, zone)
    return _to_response(updated)


@router.delete(
    "/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a zone",
)
async def delete_zone(
    zone_id: Annotated[str, Path(..., description="Zone ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> Response:
    """Delete a zone. Admin only. Returns 204 on success, 404 if not found."""
    ok = await ZoneService.delete(db, zone_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Zone not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
