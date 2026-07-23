"""Pydantic schemas for Staff model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import StaffRole
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema, BaseSchema


class StaffPinCheck(BaseSchema):
    """Request body for PIN authentication."""

    staff_id: str
    pin: str = Field(..., min_length=4, max_length=20)


class StaffBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    role: StaffRole
    is_active: bool = True


class StaffCreate(StaffBase):
    pin: str = Field(
        ..., min_length=4, max_length=20
    )  # Plaintext for initial creation (hashed in service)


class StaffUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    role: StaffRole | None = None
    is_active: bool | None = None
    pin: str | None = Field(None, min_length=4, max_length=20)  # For PIN updates


class StaffPinUpdate(BaseSchema):
    """Request body for a PIN change (hashed in the service)."""

    pin: str = Field(..., min_length=4, max_length=20)


class StaffResponse(StaffBase, BaseResponseSchema):
    """NO pin_hash or token_version here."""

    id: str
    updated_at: AwareDatetime


class TokenResponse(BaseSchema):
    """Response body for successful authentication."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105 (standard OAuth2 token type, not a password)
    expires_in: int  # seconds
    staff: StaffResponse
