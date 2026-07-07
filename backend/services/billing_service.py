"""Billing engine -- rate resolution and time charge calculation.

Replaces the Phase 2 stub with production logic.  All arithmetic is
integer-only in paise.  The LockedRate returned by ``resolve_rate`` is
stored on the session record so future rate changes do not affect
in-progress sessions (FR-BILL-003).
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException  # noqa: TCH001
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ws_manager import AgentOfflineError
from backend.core.ws_manager import manager as ws_manager
from backend.models import GamingSession, Invoice, SeatStatus, SessionStatus
from backend.models._enums import (
    AuditAction,
    InvoiceLineItemType,
    PaymentMethod,
    PricingModel,
)
from backend.models.staff import Staff
from backend.schemas.invoice import InvoiceResponse

if TYPE_CHECKING:
    pass

import backend.repositories.invoice_repo as invoice_repo
import backend.repositories.package_repo as package_repo
import backend.repositories.seat_repo as seat_repo
import backend.repositories.session_repo as session_repo
import backend.repositories.zone_repo as zone_repo
from backend.services import audit_service

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Public types
# ------------------------------------------------------------------


@dataclass(frozen=True)
class LockedRate:
    rate_paise: int
    pricing_model: PricingModel
    block_minutes: int | None = None


def _per_minute_rate(locked_rate: LockedRate) -> int:
    """Return the per-minute paise rate for credit display purposes."""
    model = locked_rate.pricing_model
    if model == PricingModel.PER_MINUTE:
        return locked_rate.rate_paise
    if model == PricingModel.FLAT_HOURLY:
        return locked_rate.rate_paise // 60
    if model == PricingModel.TIME_BLOCK:
        block = locked_rate.block_minutes or 1
        return locked_rate.rate_paise // block
    return 0


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


# ------------------------------------------------------------------
# Checkout flow (Feature 3.1.2)
# ------------------------------------------------------------------


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure a timezone-aware datetime.

    SQLite sometimes strips timezone info; re-attach UTC when missing.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _compute_elapsed_seconds(session: GamingSession) -> int:
    """Return billable elapsed seconds for a session (>= 0)."""
    total_paused = session.total_paused_seconds or 0
    if session.started_at is None:
        raise HTTPException(status_code=500, detail="Session started_at is missing")
    started_at = _ensure_utc(session.started_at)
    if started_at is None:
        raise HTTPException(status_code=500, detail="Session started_at is missing")
    paused_at = _ensure_utc(session.paused_at)
    if paused_at:
        elapsed = (paused_at - started_at).total_seconds() - total_paused
    else:
        elapsed = (datetime.now(UTC) - started_at).total_seconds() - total_paused
    return max(0, int(elapsed))


async def _print_receipt(
    invoice: InvoiceResponse,
    seat_name: str,
    duration_seconds: int,
) -> None:
    """Trigger receipt printing asynchronously (non-blocking).

    Reads printer config, builds InvoiceResponse, and dispatches to
    the print service.  Failures are logged as warnings but never
    raised.
    """
    from backend.core.config import get_config
    from backend.services.print_service import print_receipt

    try:
        config = get_config()
    except RuntimeError:
        # Config not available (e.g. CI) — skip printing gracefully
        return

    await print_receipt(
        invoice=invoice,
        cafe_name=config.cafe_name,
        config=config,
        duration_seconds=duration_seconds,
        seat_name=seat_name,
    )


async def checkout_session(
    db: AsyncSession,
    session_id: str,
    payment_method: PaymentMethod,
    staff: Staff | None = None,
) -> Invoice:
    """Complete a gaming session and return the generated invoice.

    Steps:
    1.  Load + validate session (must be ACTIVE or PAUSED).
    2.  Compute elapsed time adjusted for pauses.
    3.  Build LockedRate and calculate time charge.
    4.  Compute total (POS items are stub; Feature 3.1.4).
    5.  Create Invoice in DB.
    6.  Update session -> COMPLETED, ended_at = now.
    7.  Update seat -> AVAILABLE.
    8.  Broadcast seat_updated to dashboards.
    9.  Send SHOW_OVERLAY to agent.
    10. Trigger receipt print (non-blocking).
    11. Audit log entry: CHECKOUT.
    12. Return Invoice.
    """
    # 1. Load + validate session
    session_obj = await session_repo.get_by_id(db, session_id)
    if session_obj is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_obj.status not in (SessionStatus.ACTIVE, SessionStatus.PAUSED):
        raise HTTPException(status_code=409, detail="Session not active or paused")

    # 2. Compute elapsed time
    elapsed = _compute_elapsed_seconds(session_obj)

    # 3. Build LockedRate and time charge (+ package drawdown)
    locked = LockedRate(
        rate_paise=session_obj.locked_rate_paise,
        pricing_model=session_obj.locked_pricing_model,
    )

    # 3b. Package drawdown (Feature 3.1.3)
    package_credit_paise = 0
    package_minutes_used = 0
    entitlement_id = session_obj.package_entitlement_id

    if entitlement_id:
        elapsed_minutes = math.ceil(elapsed / 60)
        success = await package_repo.drawdown_minutes(
            db, entitlement_id, elapsed_minutes
        )
        if success:
            package_minutes_used = elapsed_minutes
        else:
            entitlement = await package_repo.get_entitlement_by_id(db, entitlement_id)
            remaining = entitlement.remaining_minutes if entitlement else 0
            if remaining > 0:
                await package_repo.drawdown_minutes(db, entitlement_id, remaining)
                package_minutes_used = remaining

        # Update exhausted status
        if package_minutes_used > 0:
            entitlement = await package_repo.get_entitlement_by_id(db, entitlement_id)
            # Raw SQL bypassed ORM; force re-read from DB
            if entitlement is not None:
                await db.refresh(entitlement)
            if entitlement and entitlement.remaining_minutes == 0:
                from backend.models._enums import EntitlementStatus

                entitlement.status = EntitlementStatus.EXHAUSTED
                db.add(entitlement)

        per_minute = _per_minute_rate(locked)
        package_credit_paise = package_minutes_used * per_minute

    # 3c. Calculate time charge (overflow only)
    if package_minutes_used > 0:
        overflow_seconds = max(0, elapsed - package_minutes_used * 60)
        time_charge = (
            calculate_time_charge(overflow_seconds, locked)
            if overflow_seconds > 0
            else 0
        )
    else:
        time_charge = calculate_time_charge(elapsed, locked)

    # 4. Compute total (POS items are stub for now -- Feature 3.1.4)
    pos_total_paise = 0
    discount_paise = session_obj.discount_paise or 0
    total_paise = max(0, time_charge + pos_total_paise - discount_paise)

    # 5. Create Invoice with package credit
    invoice = await invoice_repo.create(
        db,
        session_id=session_obj.id,
        member_id=session_obj.member_id,
        shift_id=session_obj.shift_id,
        time_charge_paise=time_charge,
        package_credit_used_paise=package_credit_paise,
        discount_paise=discount_paise,
        pos_total_paise=pos_total_paise,
        total_paise=total_paise,
        payment_method=payment_method,
    )

    # 5b. Create invoice line items
    if package_credit_paise > 0:
        per_minute = _per_minute_rate(locked)
        await invoice_repo.create_line_item(
            db,
            invoice_id=invoice.id,
            type=InvoiceLineItemType.PACKAGE_CREDIT,
            description="Package time credit",
            quantity=package_minutes_used,
            unit_price_paise=per_minute,
            total_paise=package_credit_paise,
        )
    if time_charge > 0:
        per_minute = _per_minute_rate(locked)
        overflow_minutes = max(1, math.ceil((elapsed - package_minutes_used * 60) / 60))
        await invoice_repo.create_line_item(
            db,
            invoice_id=invoice.id,
            type=InvoiceLineItemType.TIME_CHARGE,
            description="Time charge",
            quantity=overflow_minutes,
            unit_price_paise=per_minute,
            total_paise=time_charge,
        )

    # 6. Update session -> COMPLETED
    session_obj.status = SessionStatus.COMPLETED
    session_obj.ended_at = datetime.now(UTC)
    await session_repo.update(db, session_obj)

    # 7. Update seat -> AVAILABLE
    seat = await seat_repo.get_by_id(db, session_obj.seat_id)
    if seat:
        seat.status = SeatStatus.AVAILABLE
        await seat_repo.update(db, seat)

        # 8. Broadcast seat_updated to dashboards
        try:
            await ws_manager.broadcast_to_dashboards(
                "seat_updated",
                {
                    "id": seat.id,
                    "name": seat.name,
                    "status": seat.status.value,
                    "current_session_id": None,
                },
            )
        except Exception:
            logger.warning(
                "Failed to broadcast seat_updated for %s", seat.id, exc_info=True
            )

    # 9. Send SHOW_OVERLAY to agent
    try:
        await ws_manager.send_to_agent(session_obj.seat_id, {"type": "SHOW_OVERLAY"})
    except AgentOfflineError:
        logger.warning(
            "Agent offline for seat %s — SHOW_OVERLAY not sent", session_obj.seat_id
        )

    # 10. Trigger receipt print (non-blocking)
    from backend.schemas.invoice import InvoiceResponse

    seat_name = seat.name if seat else session_obj.seat_id
    # SQLite strips timezone info on datetime reads; restore it explicitly
    # so Pydantic's AwareDatetime is satisfied.
    invoice_response = InvoiceResponse(
        id=invoice.id,
        session_id=invoice.session_id,
        member_id=invoice.member_id,
        shift_id=invoice.shift_id,
        time_charge_paise=invoice.time_charge_paise,
        package_credit_used_paise=invoice.package_credit_used_paise,
        discount_paise=invoice.discount_paise,
        pos_total_paise=invoice.pos_total_paise,
        total_paise=invoice.total_paise,
        payment_method=invoice.payment_method,
        created_at=_ensure_utc(invoice.created_at),
        line_items=[],
    )
    asyncio.create_task(_print_receipt(invoice_response, seat_name, elapsed))

    # 11. Audit log
    await audit_service.log(
        db,
        action=AuditAction.CHECKOUT,
        entity_type="session",
        entity_id=session_obj.id,
        staff_id=staff.id if staff else None,
        detail=f"total_paise={total_paise}",
    )

    # 12. Return Invoice
    return invoice
