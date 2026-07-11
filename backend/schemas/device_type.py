from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class DeviceTypeBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=255)


class DeviceTypeCreate(DeviceTypeBase):
    pass


class DeviceTypeUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=255)


class DeviceTypeResponse(DeviceTypeBase, BaseResponseSchema):
    id: str
    created_at: AwareDatetime
    updated_at: AwareDatetime
