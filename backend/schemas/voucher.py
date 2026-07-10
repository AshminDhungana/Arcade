"""Pydantic schemas for Voucher model."""

from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, Field, model_validator

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


# NEW: Batch generation schemas
class VoucherBatchCreate(BaseCreateSchema):
    count: Annotated[
        int,
        Field(ge=1, le=10000, description="Number of vouchers to generate (1-10000)"),
    ]
    value_paise: int | None = Field(
        default=None,
        ge=1,
        description="Monetary value in paise (mutually exclusive with value_minutes)",
    )
    value_minutes: int | None = Field(
        default=None,
        ge=1,
        description="Time value in minutes (mutually exclusive with value_paise)",
    )
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,  # max 10 years
        description="Days until vouchers expire",
    )

    @model_validator(mode="after")
    def _validate_one_value(self) -> VoucherBatchCreate:
        if self.value_paise is not None and self.value_minutes is not None:
            raise ValueError("Only one of value_paise or value_minutes may be set")
        if self.value_paise is None and self.value_minutes is None:
            raise ValueError("Either value_paise or value_minutes must be set")
        return self


class VoucherBatchResponse(BaseResponseSchema):
    batch_id: str
    count: int
    vouchers: list[VoucherResponse]


# NEW: Redemption schema (includes member_id)
class VoucherRedeemRequest(BaseCreateSchema):
    code: Annotated[
        str,
        Field(min_length=12, max_length=12, description="12-character voucher code"),
    ]
    member_id: Annotated[
        str,
        Field(min_length=1, max_length=32, description="Member ID to credit"),
    ]
