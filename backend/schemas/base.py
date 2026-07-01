"""Shared base classes for all Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Common settings for all schemas."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class BaseCreateSchema(BaseSchema):
    """Base for request (CREATE) schemas."""


class BaseResponseSchema(BaseSchema):
    """Base for response schemas with ORM-to-Pydantic support."""

    model_config = ConfigDict(
        from_attributes=True, str_strip_whitespace=True, extra="forbid"
    )
