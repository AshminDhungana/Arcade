from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class PeakScheduleBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    is_peak: bool = Field(default=True)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: str = Field(..., max_length=5)
    end_time: str = Field(..., max_length=5)
    surcharge_paise: int = Field(default=0, ge=0)


class PeakScheduleCreate(PeakScheduleBase):
    pass


class PeakScheduleUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    is_peak: bool | None = None
    day_of_week: int | None = Field(None, ge=0, le=6)
    start_time: str | None = Field(None, max_length=5)
    end_time: str | None = Field(None, max_length=5)
    surcharge_paise: int | None = Field(None, ge=0)


class PeakScheduleResponse(PeakScheduleBase, BaseResponseSchema):
    id: str
    created_at: AwareDatetime
    updated_at: AwareDatetime
