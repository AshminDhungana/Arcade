"""Pydantic schemas for Package and MemberPackageEntitlement models."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import EntitlementStatus, PackageType, PaymentMethod
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class PackageBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    type: PackageType
    total_minutes: int = Field(..., ge=1)
    price_paise: int = Field(..., ge=0)
    valid_days: int | None = None
    zone_restriction_id: str | None = None
    is_active: bool = True


class PackageCreate(PackageBase):
    pass


class PackageUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    type: PackageType | None = None
    total_minutes: int | None = Field(None, ge=1)
    price_paise: int | None = Field(None, ge=0)
    valid_days: int | None = None
    zone_restriction_id: str | None = None
    is_active: bool | None = None


class PackageResponse(PackageBase, BaseResponseSchema):
    id: str


class MemberPackageEntitlementBase(BaseCreateSchema):
    member_id: str
    package_id: str
    remaining_minutes: int = Field(..., ge=1)
    expires_at: AwareDatetime | None = None


class MemberPackageEntitlementCreate(MemberPackageEntitlementBase):
    payment_method: PaymentMethod


class SellPackageRequest(BaseCreateSchema):
    """Request schema for selling a package to a member."""

    package_id: str
    payment_method: PaymentMethod


class MemberPackageEntitlementUpdate(BaseCreateSchema):
    remaining_minutes: int | None = Field(None, ge=0)
    status: EntitlementStatus | None = None
    expires_at: AwareDatetime | None = None


class MemberPackageEntitlementResponse(
    MemberPackageEntitlementBase, BaseResponseSchema
):
    id: str
    status: EntitlementStatus
    purchased_at: AwareDatetime
    updated_at: AwareDatetime
