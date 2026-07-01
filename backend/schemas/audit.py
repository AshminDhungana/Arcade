"""Pydantic schemas for AuditLog model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import AuditAction
from backend.schemas.base import BaseResponseSchema


class AuditLogResponse(BaseResponseSchema):
    id: str
    timestamp: AwareDatetime
    staff_id: str | None = None
    action: AuditAction
    entity_type: str = Field(..., max_length=50)
    entity_id: str = Field(..., max_length=32)
    detail: str | None = None
