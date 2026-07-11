"""Pydantic schema for WalletTransaction."""

from __future__ import annotations

from pydantic import AwareDatetime

from backend.schemas.base import BaseResponseSchema


class WalletTransactionResponse(BaseResponseSchema):
    member_id: str
    type: str
    amount_paise: int
    balance_after_paise: int
    payment_method: str
    staff_id: str | None
    reference_id: str | None
    created_at: AwareDatetime
