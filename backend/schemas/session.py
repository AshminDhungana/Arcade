"""Pydantic schemas for GamingSession model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import PaymentMethod, PricingModel, SessionStatus
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class SessionBase(BaseCreateSchema):
    seat_id: str
    member_id: str | None = None
    shift_id: str | None = None
    locked_rate_paise: int = Field(..., ge=0)
    locked_pricing_model: PricingModel
    package_entitlement_id: str | None = None
    promotion_id: str | None = None
    discount_paise: int = Field(0, ge=0)
    payment_method: PaymentMethod | None = None


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseCreateSchema):
    member_id: str | None = None
    shift_id: str | None = None
    status: SessionStatus | None = None
    discount_paise: int | None = Field(None, ge=0)
    payment_method: PaymentMethod | None = None


class SessionResponse(SessionBase, BaseResponseSchema):
    id: str
    status: SessionStatus
    started_at: AwareDatetime
    ended_at: AwareDatetime | None = None
    paused_at: AwareDatetime | None = None
    total_paused_seconds: int = 0
    assigned_end_at: AwareDatetime | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
