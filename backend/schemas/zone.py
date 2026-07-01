"""Pydantic schemas for Zone model."""

from __future__ import annotations

from pydantic import Field

from backend.models._enums import PricingModel
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class ZoneBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    rate_per_minute_paise: int = Field(..., ge=0)
    rate_per_hour_paise: int = Field(..., ge=0)
    pricing_model: PricingModel
    block_minutes: int | None = Field(None, ge=1)


class ZoneCreate(ZoneBase):
    pass


class ZoneUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    rate_per_minute_paise: int | None = Field(None, ge=0)
    rate_per_hour_paise: int | None = Field(None, ge=0)
    pricing_model: PricingModel | None = None
    block_minutes: int | None = Field(None, ge=1)


class ZoneResponse(ZoneBase, BaseResponseSchema):
    id: str
