"""Pydantic schemas for analytics summary data."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.schemas.base import BaseSchema


class AnalyticsSummary(BaseSchema):
    total_revenue_paise: int = Field(0, ge=0)
    session_count: int = Field(0, ge=0)
    average_duration_seconds: float = 0.0
    today_new_members: int = Field(0, ge=0)
    today_active_members: int = Field(0, ge=0)
    current_shift_id: str | None = None
    shift_opened_at: AwareDatetime | None = None


class AnalyticsSummaryRequest(BaseSchema):
    date_from: AwareDatetime
    date_to: AwareDatetime
