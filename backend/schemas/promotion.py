"""Pydantic schemas for Promotion model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import DiscountType, PromotionType
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class PromotionBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    type: PromotionType
    discount_type: DiscountType
    discount_value: int = Field(..., ge=0)
    active_days: str | None = Field(None, max_length=255)
    active_from_hour: int | None = Field(None, ge=0, le=23)
    active_to_hour: int | None = Field(None, ge=0, le=23)
    min_group_size: int | None = Field(None, ge=1)
    zone_restriction_id: str | None = None
    is_active: bool = True
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None


class PromotionCreate(PromotionBase):
    pass


class PromotionUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    type: PromotionType | None = None
    discount_type: DiscountType | None = None
    discount_value: int | None = Field(None, ge=0)
    active_days: str | None = Field(None, max_length=255)
    active_from_hour: int | None = Field(None, ge=0, le=23)
    active_to_hour: int | None = Field(None, ge=0, le=23)
    min_group_size: int | None = Field(None, ge=1)
    zone_restriction_id: str | None = None
    is_active: bool | None = None
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None


class PromotionResponse(PromotionBase, BaseResponseSchema):
    id: str
