"""Pydantic schemas for MenuItem and SessionPOSItem models."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class MenuItemBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    category: str | None = Field(None, max_length=100)
    price_paise: int = Field(..., ge=0)
    stock_quantity: int | None = None
    low_stock_threshold: int | None = None
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=100)
    price_paise: int | None = Field(None, ge=0)
    stock_quantity: int | None = None
    low_stock_threshold: int | None = None
    is_available: bool | None = None


class MenuItemResponse(MenuItemBase, BaseResponseSchema):
    id: str
    updated_at: AwareDatetime


class SessionPOSItemBase(BaseCreateSchema):
    session_id: str
    menu_item_id: str
    quantity: int = Field(1, ge=1)
    unit_price_paise: int = Field(..., ge=0)


class SessionPOSItemCreate(SessionPOSItemBase):
    pass


class SessionPOSItemResponse(SessionPOSItemBase, BaseResponseSchema):
    id: str
    added_at: AwareDatetime
