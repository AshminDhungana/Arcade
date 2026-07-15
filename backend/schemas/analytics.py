"""Pydantic schemas for analytics summary data."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.schemas.base import BaseResponseSchema


class BusiestHour(BaseResponseSchema):
    hour: int = Field(ge=0, le=23)
    session_count: int = Field(ge=0)


class DailyRevenue(BaseResponseSchema):
    date: str
    total_paise: int = Field(ge=0)


class DailyCount(BaseResponseSchema):
    date: str
    count: int = Field(ge=0)


class TopPosItem(BaseResponseSchema):
    menu_item_id: str
    name: str
    quantity: int = Field(ge=0)


class ZoneUtilisation(BaseResponseSchema):
    zone_id: str
    zone_name: str
    session_hours: float = Field(ge=0)
    available_hours: float = Field(ge=0)
    utilisation_pct: float = Field(ge=0)


class TopSpender(BaseResponseSchema):
    member_id: str
    name: str
    total_paise: int = Field(ge=0)


class MemberStats(BaseResponseSchema):
    new_today: int = Field(ge=0)
    active_last_30d: int = Field(ge=0)
    top_spenders: list[TopSpender] = Field(default_factory=list)


class HealthAlert(BaseResponseSchema):
    seat_id: str
    seat_name: str
    reasons: list[str] = Field(default_factory=list)


class UpcomingReservation(BaseResponseSchema):
    reservation_id: str
    seat_id: str
    seat_name: str
    customer_name: str
    reserved_from: AwareDatetime


class WolSuccessRate(BaseResponseSchema):
    seat_id: str
    seat_name: str
    attempts: int = Field(ge=0)
    successes: int = Field(ge=0)
    rate_pct: float = Field(ge=0)


class AnalyticsSummary(BaseResponseSchema):
    total_revenue_paise: int = Field(ge=0)
    session_count: int = Field(ge=0)
    average_duration_seconds: float = 0.0
    busiest_hour: BusiestHour | None = None
    weekly_revenue: list[DailyRevenue] = Field(default_factory=list)
    top_pos_items: list[TopPosItem] = Field(default_factory=list)
    member_registration_trend: list[DailyCount] = Field(default_factory=list)
    zone_utilisation: list[ZoneUtilisation] = Field(default_factory=list)
    member_stats: MemberStats
    health_alerts: list[HealthAlert] = Field(default_factory=list)
    upcoming_reservations: list[UpcomingReservation] = Field(default_factory=list)
    wol_success_rates: list[WolSuccessRate] = Field(default_factory=list)
    current_shift_id: str | None = None
    shift_opened_at: AwareDatetime | None = None
