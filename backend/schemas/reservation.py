"""Pydantic schemas for Reservation model."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import ReservationStatus
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class ReservationBase(BaseCreateSchema):
    seat_id: str
    customer_name: str = Field(..., max_length=255)
    member_id: str | None = None
    reserved_from: AwareDatetime
    reserved_until: AwareDatetime | None = None
    group_reservation_id: str | None = None
    notes: str | None = Field(None, max_length=1000)
    created_by_staff_id: str | None = None


class ReservationCreate(ReservationBase):
    status: ReservationStatus = ReservationStatus.PENDING


class ReservationUpdate(BaseCreateSchema):
    seat_id: str | None = None
    customer_name: str | None = Field(None, max_length=255)
    member_id: str | None = None
    reserved_from: AwareDatetime | None = None
    reserved_until: AwareDatetime | None = None
    group_reservation_id: str | None = None
    notes: str | None = Field(None, max_length=1000)
    status: ReservationStatus | None = None


class ReservationResponse(ReservationBase, BaseResponseSchema):
    id: str
    status: ReservationStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime
