"""Pydantic schemas for health metrics (dashboard/agent)."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.schemas.base import BaseSchema


class HealthMetricsRequest(BaseSchema):
    seat_id: str
    cpu_pct: float = Field(..., ge=0, le=100)
    ram_pct: float = Field(..., ge=0, le=100)
    cpu_temp: float | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None
    timestamp: AwareDatetime


class HealthMetricsResponse(BaseSchema):
    seat_id: str
    cpu_pct: float
    ram_pct: float
    cpu_temp: float | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None
    timestamp: AwareDatetime
