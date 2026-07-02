"""Billing rate resolver — Phase 2 minimal stub.

The full billing engine (promotions, peak hours, package drawdown)
lands in Phase 3.  This module only exists so that
``session_service.start_session()`` can call a stable interface today.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models._enums import PricingModel


@dataclass(frozen=True)
class LockedRate:
    rate_paise: int
    pricing_model: PricingModel
    block_minutes: int | None = None


async def resolve_rate(*, seat_id: str, member_id: str | None = None) -> LockedRate:
    """Return the locked rate for a session start.

    Stub implementation — always returns zero rate and ``PER_MINUTE`` model.
    Phase 3 will replace this with real zone / promotion / member logic.
    """
    return LockedRate(rate_paise=0, pricing_model=PricingModel.PER_MINUTE)
