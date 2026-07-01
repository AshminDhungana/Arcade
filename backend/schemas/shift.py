"""Pydantic schemas for Shift model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import ShiftStatus
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class ShiftBase(BaseCreateSchema):
    opened_by_staff_id: str


class ShiftCreate(ShiftBase):
    pass


class ShiftUpdate(BaseCreateSchema):
    closed_by_staff_id: str | None = None
    float_paise: int | None = Field(None, ge=0)
    counted_paise: int | None = Field(None, ge=0)
    status: ShiftStatus | None = None


class ShiftResponse(ShiftBase, BaseResponseSchema):
    id: str
    closed_by_staff_id: str | None = None
    opened_at: AwareDatetime
    closed_at: AwareDatetime | None = None
    float_paise: int
    counted_paise: int | None = None
    status: ShiftStatus
