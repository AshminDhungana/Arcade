"""Pydantic schemas for Voucher model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import VoucherStatus
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class VoucherBase(BaseCreateSchema):
    code: str = Field(..., max_length=12)
    value_paise: int | None = None
    value_minutes: int | None = None
    expires_at: AwareDatetime | None = None
    batch_id: str


class VoucherCreate(VoucherBase):
    pass


class VoucherUpdate(BaseCreateSchema):
    status: VoucherStatus | None = None
    redeemed_by_member_id: str | None = None
    redeemed_at: AwareDatetime | None = None


class VoucherResponse(VoucherBase, BaseResponseSchema):
    id: str
    status: VoucherStatus
    redeemed_by_member_id: str | None = None
    redeemed_at: AwareDatetime | None = None
    created_at: AwareDatetime
