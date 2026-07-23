"""Business logic for staff-zone assignments."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models._enums import AuditAction, StaffRole
from backend.models.staff import Staff
from backend.models.zone import Zone
from backend.repositories import staff_zone_repo, zone_repo
from backend.services import audit_service


class StaffZoneService:
    @staticmethod
    async def assign_zone(
        db: AsyncSession,
        *,
        staff_id: str,
        zone_id: str,
        admin: Staff,
    ) -> None:
        """Grant zone access to a staff member. Admin only."""
        # Verify staff exists
        target = await db.get(Staff, staff_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Staff not found")

        # Verify zone exists
        zone = await db.get(Zone, zone_id)
        if zone is None:
            raise HTTPException(status_code=404, detail="Zone not found")

        # Check if already assigned (active)
        existing = await staff_zone_repo.is_staff_assigned_to_zone(
            db, staff_id=staff_id, zone_id=zone_id
        )
        if existing:
            raise HTTPException(
                status_code=409, detail="Staff already has access to this zone"
            )

        # Create assignment
        await staff_zone_repo.assign_zone(
            db, staff_id=staff_id, zone_id=zone_id, granted_by=admin.id
        )

        # Audit log
        await audit_service.log(
            db,
            action=AuditAction.STAFF_ZONE_ASSIGNED,
            entity_type="staff_zone",
            entity_id=f"{staff_id}:{zone_id}",
            staff_id=admin.id,
            detail=f"Granted zone '{zone.name}' to staff '{target.name}'",
        )

    @staticmethod
    async def revoke_zone(
        db: AsyncSession,
        *,
        staff_id: str,
        zone_id: str,
        admin: Staff,
    ) -> None:
        """Revoke zone access from a staff member. Admin only."""
        target = await db.get(Staff, staff_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Staff not found")

        zone = await db.get(Zone, zone_id)
        if zone is None:
            raise HTTPException(status_code=404, detail="Zone not found")

        ok = await staff_zone_repo.revoke_zone(db, staff_id=staff_id, zone_id=zone_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Assignment not found")

        await audit_service.log(
            db,
            action=AuditAction.STAFF_ZONE_REVOKED,
            entity_type="staff_zone",
            entity_id=f"{staff_id}:{zone_id}",
            staff_id=admin.id,
            detail=f"Revoked zone '{zone.name}' from staff '{target.name}'",
        )

    @staticmethod
    async def get_accessible_zones(db: AsyncSession, staff: Staff) -> Sequence[Zone]:
        """Return zones the staff member can access."""
        if staff.role == StaffRole.ADMIN:
            # Admins see all zones
            return await zone_repo.list(db)

        zone_ids = await staff_zone_repo.get_zone_ids_for_staff(db, staff.id)
        if not zone_ids:
            return []

        zones = []
        for zid in zone_ids:
            zone = await zone_repo.get_by_id(db, zid)
            if zone:
                zones.append(zone)
        return zones

    @staticmethod
    async def list_assignments_for_staff(
        db: AsyncSession, staff_id: str
    ) -> list[dict[str, object]]:
        """Return zone assignments with zone details for admin UI."""

        assignments = await staff_zone_repo.list_zones_for_staff(db, staff_id)
        result = []
        for a in assignments:
            zone = await db.get(Zone, a.zone_id)
            granter = await db.get(Staff, a.granted_by)
            result.append(
                {
                    "zone_id": a.zone_id,
                    "zone_name": zone.name if zone else "Unknown",
                    "granted_by": granter.name if granter else "Unknown",
                    "granted_at": a.granted_at,
                    "is_active": a.is_active,
                }
            )
        return result
