"""Pydantic schemas for Member model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import MemberTier, PaymentMethod
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class MemberBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=50)
    birth_month: int | None = Field(None, ge=1, le=12)


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    birth_month: int | None = Field(None, ge=1, le=12)


class MemberResponse(MemberBase, BaseResponseSchema):
    id: str
    wallet_balance_paise: int
    loyalty_points: int
    tier: MemberTier
    total_visits: int
    total_seconds_played: int
    created_at: AwareDatetime
    updated_at: AwareDatetime


class TopupRequest(BaseCreateSchema):
    """Request body for wallet topup."""

    amount_paise: int = Field(..., gt=0)
    payment_method: PaymentMethod
