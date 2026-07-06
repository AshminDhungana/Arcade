"""Billing engine -- rate resolution and time charge calculation.

Replaces the Phase 2 stub with production logic.  All arithmetic is
integer-only in paise.  The LockedRate returned by ``resolve_rate`` is
stored on the session record so future rate changes do not affect
in-progress sessions (FR-BILL-003).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models._enums import PricingModel

if TYPE_CHECKING:
    pass

import backend.repositories.seat_repo as seat_repo
import backend.repositories.zone_repo as zone_repo

# ------------------------------------------------------------------
# Public types
# ------------------------------------------------------------------


@dataclass(frozen=True)
class LockedRate:
    rate_paise: int
    pricing_model: PricingModel
    block_minutes: int | None = None


# ------------------------------------------------------------------
# Time charge calculation (pure math, no DB)
# ------------------------------------------------------------------


def calculate_time_charge(elapsed_seconds: int, locked_rate: LockedRate) -> int:
    """Return the paise charge for elapsed_seconds under the given locked rate.

    All three pricing models use math.ceil so any started unit is
    charged in full (NFR-DATA-002).
    """
    if elapsed_seconds <= 0:
        return 0

    model = locked_rate.pricing_model
    rate = locked_rate.rate_paise

    if model == PricingModel.PER_MINUTE:
        minutes = math.ceil(elapsed_seconds / 60)
        return minutes * rate

    if model == PricingModel.FLAT_HOURLY:
        hours = math.ceil(elapsed_seconds / 3600)
        return hours * rate

    if model == PricingModel.TIME_BLOCK:
        block = locked_rate.block_minutes
        if block is None or block <= 0:
            return 0
        blocks = math.ceil(elapsed_seconds / (block * 60))
        return blocks * rate

    return 0


# ------------------------------------------------------------------
# Rate resolution (async, DB access)
# ------------------------------------------------------------------


async def resolve_rate(
    db: AsyncSession,
    seat_id: str,
    member_id: str | None = None,
    now: datetime | None = None,
) -> LockedRate:
    """Resolve the LockedRate for a session start on *seat_id*.

    The *member_id* and *now* parameters are accepted for future
    extensibility (member discounts, happy-hour rates, etc.) but are
    currently ignored.
    """
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found")

    zone = await zone_repo.get_by_id(db, seat.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Zone {seat.zone_id} not found")

    _ = member_id  # Reserved for future member-discount logic
    _ = now  # Reserved for future happy-hour / time-dependent rates

    model = zone.pricing_model
    if model == PricingModel.PER_MINUTE:
        return LockedRate(
            rate_paise=zone.rate_per_minute_paise,
            pricing_model=model,
            block_minutes=zone.block_minutes,
        )
    elif model == PricingModel.FLAT_HOURLY:
        return LockedRate(
            rate_paise=zone.rate_per_hour_paise,
            pricing_model=model,
            block_minutes=zone.block_minutes,
        )
    elif model == PricingModel.TIME_BLOCK:
        return LockedRate(
            rate_paise=(zone.block_minutes or 0) * zone.rate_per_minute_paise,
            pricing_model=model,
            block_minutes=zone.block_minutes,
        )

    # Should not be reached with well-formed PricingModel
    raise HTTPException(status_code=400, detail=f"Unknown pricing model {model}")
