"""Peak/Off-Peak Schedules API router — admin-gated.

Routes::

    POST   /api/schedules           → create schedule (Admin)
    GET    /api/schedules           → list all schedules (Admin)
    GET    /api/schedules/{id}      → get one schedule (Admin)
    PUT    /api/schedules/{id}      → update schedule (Admin)
    DELETE /api/schedules/{id}      → delete schedule (Admin)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.peak_schedule import PeakSchedule
from backend.models.staff import Staff
from backend.schemas.peak_schedule import (
    PeakScheduleCreate,
    PeakScheduleResponse,
    PeakScheduleUpdate,
)
from backend.services.peak_schedule_service import PeakScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """SQLite may strip tzinfo; re-attach UTC so AwareDatetime validates.

    Mirrors ``auth_service._ensure_tz``.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _to_response(sc: PeakSchedule) -> PeakScheduleResponse:
    """Normalise updated_at/created_at timezone and build a PeakScheduleResponse."""
    sc.updated_at = _ensure_tz(sc.updated_at)  # type: ignore[assignment]
    sc.created_at = _ensure_tz(sc.created_at)  # type: ignore[assignment]
    return PeakScheduleResponse.model_validate(sc)


@router.post(
    "",
    response_model=PeakScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a schedule",
)
async def create_schedule(
    body: Annotated[PeakScheduleCreate, Body(description="New schedule details")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> PeakScheduleResponse:
    """Create a new schedule. Admin only."""
    created = await PeakScheduleService.create(
        db,
        name=body.name,
        is_peak=body.is_peak,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
        surcharge_paise=body.surcharge_paise,
    )
    return _to_response(created)


@router.get(
    "",
    response_model=list[PeakScheduleResponse],
    summary="List all schedules",
)
async def list_schedules(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> list[PeakScheduleResponse]:
    """List all schedules. Admin only."""
    schedules = await PeakScheduleService.list(db)
    return [_to_response(s) for s in schedules]


@router.get(
    "/{schedule_id}",
    response_model=PeakScheduleResponse,
    summary="Get a schedule by ID",
)
async def get_schedule(
    schedule_id: Annotated[str, Path(..., description="Schedule ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> PeakScheduleResponse:
    """Get a schedule by ID. Admin only."""
    sc = await PeakScheduleService.get_by_id(db, schedule_id)
    if sc is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Schedule not found")
    return _to_response(sc)


@router.put(
    "/{schedule_id}",
    response_model=PeakScheduleResponse,
    summary="Update a schedule",
)
async def update_schedule(
    schedule_id: Annotated[str, Path(..., description="Schedule ID")],
    body: Annotated[PeakScheduleUpdate, Body(description="Schedule fields to update")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> PeakScheduleResponse:
    """Update a schedule (PATCH semantics — all fields optional). Admin only."""
    sc = await PeakScheduleService.get_by_id(db, schedule_id)
    if sc is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Schedule not found")

    # Apply only fields that were provided (exclude_unset = PATCH semantics)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sc, field, value)

    updated = await PeakScheduleService.update(db, sc)
    return _to_response(updated)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a schedule",
)
async def delete_schedule(
    schedule_id: Annotated[str, Path(..., description="Schedule ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> Response:
    """Delete a schedule. Admin only. Returns 204 on success, 404 if not found."""
    ok = await PeakScheduleService.delete(db, schedule_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Schedule not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
