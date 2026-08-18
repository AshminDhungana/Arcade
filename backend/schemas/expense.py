"""Pydantic schemas for Expense CRUD."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from backend.models._enums import ExpenseCategory
from backend.schemas.base import BaseResponseSchema


class ExpenseCreate(BaseResponseSchema):
    date: date
    category: ExpenseCategory
    amount_paise: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=1000)


class ExpenseResponse(BaseResponseSchema):
    id: str
    date: date
    category: ExpenseCategory
    amount_paise: int
    note: str | None
    logged_by_staff_id: str
    created_at: str  # ISO datetime string
