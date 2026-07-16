"""Pydantic schemas for Invoice and InvoiceLineItem models."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import InvoiceLineItemType, InvoicePrintStatus, PaymentMethod
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class InvoiceLineItemBase(BaseCreateSchema):
    type: InvoiceLineItemType
    description: str = Field(..., max_length=500)
    quantity: int = Field(1, ge=1)
    unit_price_paise: int = Field(..., ge=0)
    total_paise: int = Field(..., ge=0)


class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass


class InvoiceLineItemResponse(InvoiceLineItemBase, BaseResponseSchema):
    id: str
    invoice_id: str


class InvoiceBase(BaseCreateSchema):
    session_id: str
    member_id: str | None = None
    shift_id: str | None = None
    time_charge_paise: int = Field(0, ge=0)
    package_credit_used_paise: int = Field(0, ge=0)
    discount_paise: int = Field(0, ge=0)
    pos_total_paise: int = Field(0, ge=0)
    total_paise: int = Field(0, ge=0)
    payment_method: PaymentMethod


class InvoiceCreate(InvoiceBase):
    line_items: list[InvoiceLineItemCreate] = []


class InvoiceUpdate(BaseCreateSchema):
    pos_total_paise: int | None = Field(None, ge=0)
    discount_paise: int | None = Field(None, ge=0)
    total_paise: int | None = Field(None, ge=0)
    payment_method: PaymentMethod | None = None


class InvoiceResponse(InvoiceBase, BaseResponseSchema):
    id: str
    created_at: AwareDatetime
    print_status: InvoicePrintStatus = InvoicePrintStatus.PENDING
    line_items: list[InvoiceLineItemResponse] = []
