"""Repository for StaffZone assignments."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.staff_zone import StaffZone


async def assign_zone(
    db: AsyncSession,
    *,
    staff_id: str,
    zone_id: str,
    granted_by: str,
) -> StaffZone:
    """Grant zone access to a staff member."""
    assignment = StaffZone(staff_id=staff_id, zone_id=zone_id, granted_by=granted_by)
    db.add(assignment)
    await db.flush()
    return assignment


async def revoke_zone(db: AsyncSession, *, staff_id: str, zone_id: str) -> bool:
    """Revoke zone access (soft delete via is_active=False)."""
    result = await db.execute(
        select(StaffZone).where(
            StaffZone.staff_id == staff_id,
            StaffZone.zone_id == zone_id,
            StaffZone.is_active,  # noqa: E712
        )
    )
    assignment = result.scalars().first()
    if assignment is None:
        return False
    assignment.is_active = False
    await db.flush()
    return True


async def list_zones_for_staff(db: AsyncSession, staff_id: str) -> Sequence[StaffZone]:
    """Get all active zone assignments for a staff member."""
    result = await db.execute(
        select(StaffZone).where(
            StaffZone.staff_id == staff_id,
            StaffZone.is_active,  # noqa: E712
        )
    )
    return result.scalars().all()


async def get_zone_ids_for_staff(db: AsyncSession, staff_id: str) -> list[str]:
    """Get list of zone IDs the staff has access to."""
    result = await db.execute(
        select(StaffZone.zone_id).where(
            StaffZone.staff_id == staff_id,
            StaffZone.is_active,  # noqa: E712
        )
    )
    return [row[0] for row in result.all()]


async def is_staff_assigned_to_zone(
    db: AsyncSession, *, staff_id: str, zone_id: str
) -> bool:
    """Check if staff has active access to a zone."""
    result = await db.execute(
        select(StaffZone).where(
            StaffZone.staff_id == staff_id,
            StaffZone.zone_id == zone_id,
            StaffZone.is_active,  # noqa: E712
        )
    )
    return result.scalars().first() is not None


async def list_staff_for_zone(db: AsyncSession, zone_id: str) -> Sequence[StaffZone]:
    """Get all staff assigned to a zone (for admin UI)."""
    result = await db.execute(
        select(StaffZone).where(
            StaffZone.zone_id == zone_id,
            StaffZone.is_active,  # noqa: E712
        )
    )
    return result.scalars().all()
