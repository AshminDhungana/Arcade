"""Schemas for staff-zone assignments."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StaffZoneAssign(BaseModel):
    """Request to assign a zone to a staff member."""

    zone_id: str


class StaffZoneResponse(BaseModel):
    """Zone assignment with details."""

    model_config = ConfigDict(from_attributes=True)

    zone_id: str
    zone_name: str
    granted_by: str
    granted_at: datetime
    is_active: bool


class StaffZoneBulkAssign(BaseModel):
    """Bulk assign multiple zones to a staff member."""

    zone_ids: list[str]
