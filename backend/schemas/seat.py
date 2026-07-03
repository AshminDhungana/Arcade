"""Pydantic schemas for Seat model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import SeatStatus
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class SeatBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    zone_id: str
    mac_address: str | None = Field(None, max_length=17)
    status: SeatStatus = SeatStatus.AVAILABLE
    plug_id: str | None = Field(None, max_length=255)
    is_console: bool = False
    notes: str | None = Field(None, max_length=1000)


class SeatCreate(SeatBase):
    pass


class SeatUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    zone_id: str | None = None
    mac_address: str | None = Field(None, max_length=17)
    status: SeatStatus | None = None
    plug_id: str | None = Field(None, max_length=255)
    is_console: bool | None = None
    notes: str | None = Field(None, max_length=1000)


class SeatResponse(SeatBase, BaseResponseSchema):
    id: str
    created_at: AwareDatetime
    updated_at: AwareDatetime
    wol_attempts: int = 0
    wol_successes: int = 0
    wol_failures: int = 0
