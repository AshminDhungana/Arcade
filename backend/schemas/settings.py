"""Pydantic schemas for AppSettings model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class AppSettingsBase(BaseCreateSchema):
    key: str = Field(..., max_length=255)
    value: str = Field(..., max_length=4000)


class AppSettingsCreate(AppSettingsBase):
    pass


class AppSettingsUpdate(BaseCreateSchema):
    value: str | None = Field(None, max_length=4000)


class AppSettingsResponse(AppSettingsBase, BaseResponseSchema):
    updated_at: AwareDatetime
