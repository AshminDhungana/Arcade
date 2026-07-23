"""Staff-Zone assignment API router.

Routes::
    POST   /api/staff/{staff_id}/zones           → assign zone (Admin)
    POST   /api/staff/{staff_id}/zones/bulk      → bulk assign zones (Admin)
    GET    /api/staff/me/zones                   → my accessible zones (Cashier+)
    GET    /api/staff/{staff_id}/zones           → list assignments (Admin)
    DELETE /api/staff/{staff_id}/zones/{zone_id} → revoke zone (Admin)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_staff, require_admin
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.models.zone import Zone
from backend.schemas.staff_zone import (
    StaffZoneAssign,
    StaffZoneBulkAssign,
    StaffZoneResponse,
)
from backend.services.staff_zone_service import StaffZoneService

router = APIRouter(prefix="/staff", tags=["staff-zones"])


@router.get(
    "/me/zones",
    response_model=list[StaffZoneResponse],
    summary="Get my accessible zones",
)
async def get_my_zones(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Staff = Depends(get_current_staff),  # noqa: B008
) -> list[StaffZoneResponse]:
    """Return zones the current staff member can access. Cashier+."""
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"get_my_zones called with staff={staff.id}, role={staff.role}")
    zones = await StaffZoneService.get_accessible_zones(db, staff)
    logger.debug(f"staff_zone_service.get_accessible_zones returned {len(zones)} zones")
    for z in zones:
        logger.debug(f"  - {z.id}: {z.name}")
    result = [
        StaffZoneResponse(
            zone_id=z.id,
            zone_name=z.name,
            granted_by="",
            granted_at=datetime.now(UTC),
            is_active=True,
        )
        for z in zones
    ]
    logger.debug(f"Returning {len(result)} responses")
    return result


@router.post(
    "/{staff_id}/zones",
    response_model=StaffZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a zone to a staff member",
)
async def assign_zone(
    staff_id: Annotated[str, Path(..., description="Staff ID")],
    body: StaffZoneAssign,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin: Staff = Depends(require_admin),  # noqa: B008
) -> StaffZoneResponse:
    """Grant zone access to a staff member. Admin only."""
    await StaffZoneService.assign_zone(
        db, staff_id=staff_id, zone_id=body.zone_id, admin=admin
    )
    zone = await db.get(Zone, body.zone_id)
    granter = await db.get(Staff, admin.id)
    return StaffZoneResponse(
        zone_id=body.zone_id,
        zone_name=zone.name if zone else "Unknown",
        granted_by=granter.name if granter else "Unknown",
        granted_at=datetime.now(UTC),
        is_active=True,
    )


@router.post(
    "/{staff_id}/zones/bulk",
    response_model=list[StaffZoneResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk assign zones to a staff member",
)
async def bulk_assign_zones(
    staff_id: Annotated[str, Path(..., description="Staff ID")],
    body: StaffZoneBulkAssign,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin: Staff = Depends(require_admin),  # noqa: B008
) -> list[StaffZoneResponse]:
    """Assign multiple zones at once. Admin only."""
    results = []
    for zone_id in body.zone_ids:
        try:
            await StaffZoneService.assign_zone(
                db, staff_id=staff_id, zone_id=zone_id, admin=admin
            )
            zone = await db.get(Zone, zone_id)
            results.append(
                StaffZoneResponse(
                    zone_id=zone_id,
                    zone_name=zone.name if zone else "Unknown",
                    granted_by=admin.name,
                    granted_at=datetime.now(UTC),
                    is_active=True,
                )
            )
        except Exception:
            # Skip duplicates, continue with others
            import logging

            logging.getLogger(__name__).debug("Skipping duplicate zone assignment")
    return results


@router.get(
    "/{staff_id}/zones",
    response_model=list[StaffZoneResponse],
    summary="List zone assignments for a staff member",
)
async def list_staff_zones(
    staff_id: Annotated[str, Path(..., description="Staff ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _admin: Staff = Depends(require_admin),  # noqa: B008
) -> list[StaffZoneResponse]:
    """List all zone assignments for a staff member. Admin only."""
    assignments = await StaffZoneService.list_assignments_for_staff(db, staff_id)
    return [StaffZoneResponse(**a) for a in assignments]


@router.delete(
    "/{staff_id}/zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke zone access from a staff member",
)
async def revoke_zone(
    staff_id: Annotated[str, Path(..., description="Staff ID")],
    zone_id: Annotated[str, Path(..., description="Zone ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    admin: Staff = Depends(require_admin),  # noqa: B008
) -> None:
    """Revoke zone access from a staff member. Admin only."""
    await StaffZoneService.revoke_zone(
        db, staff_id=staff_id, zone_id=zone_id, admin=admin
    )
