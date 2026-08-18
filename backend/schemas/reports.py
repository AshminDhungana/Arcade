"""Pydantic schemas for P&L reports."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from backend.schemas.base import BaseResponseSchema


class PLSummaryResponse(BaseResponseSchema):
    period_start: date
    period_end: date
    session_revenue_paise: int = Field(ge=0)
    pos_revenue_paise: int = Field(ge=0)
    total_revenue_paise: int = Field(ge=0)
    expenses_by_category: dict[str, int] = Field(
        default_factory=dict
    )  # string keys for JSON
    total_expenses_paise: int = Field(ge=0)
    gross_profit_paise: int
    net_profit_paise: int
