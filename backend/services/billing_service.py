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

from backend.core.config import get_config
from backend.core.feature_flags import get_flag
from backend.core.security import verify_pin
from backend.core.ws_manager import AgentOfflineError
from backend.core.ws_manager import manager as ws_manager
from backend.models import GamingSession, Invoice, SeatStatus, SessionStatus
from backend.models._enums import (
    AuditAction,
    InvoiceLineItemType,
    InvoicePrintStatus,
    PaymentMethod,
    PricingModel,
)
from backend.models.staff import Staff
from backend.schemas.invoice import InvoiceResponse
from backend.services.print_service import _build_invoice_response

if TYPE_CHECKING:
    pass

import backend.repositories.inventory_repo as inventory_repo
import backend.repositories.invoice_repo as invoice_repo
import backend.repositories.package_repo as package_repo
import backend.repositories.pos_repo as pos_repo
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
    """Trigger receipt printing asynchronously (non-blocking) and track status.

    Reads printer config and dispatches to the print service, which persists
    ``print_status`` and enqueues a retry job on failure.
    """
    from backend.core.config import get_config
    from backend.services.print_service import enqueue_and_track_print

    try:
        config = get_config()
    except RuntimeError:
        # Config not available (e.g. CI) — skip printing gracefully
        return

    await enqueue_and_track_print(
        invoice.id,
        invoice,
        config.cafe_name,
        config,
        duration_seconds=duration_seconds,
        seat_name=seat_name,
    )


async def _release_held_seat(
    db: AsyncSession,
    session: GamingSession,
    invoice: Invoice,
    *,
    staff: Staff | None = None,
    override_reason: str | None = None,
) -> None:
    """Free the seat and notify the agent: the single release point.

    - seat -> AVAILABLE
    - broadcast seat_updated to dashboards
    - send SHOW_OVERLAY to the agent (AgentOfflineError swallowed)
    - Tuya power-off (best-effort, never fatal)
    - if override_reason: audit CHECKOUT_FORCED_UNPRINTED
    """
    seat = await seat_repo.get_by_id(db, session.seat_id)
    if seat:
        seat.status = SeatStatus.AVAILABLE
        await seat_repo.update(db, seat)
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

    try:
        await ws_manager.send_to_agent(session.seat_id, {"type": "SHOW_OVERLAY"})
    except AgentOfflineError:
        logger.warning(
            "Agent offline for seat %s — SHOW_OVERLAY not sent", session.seat_id
        )

    try:
        from backend.services import tuya_service

        await tuya_service.power_off(db, session.seat_id)
    except Exception:
        logger.warning(
            "Tuya power-off raised for seat %s", session.seat_id, exc_info=True
        )

    if override_reason:
        await audit_service.log(
            db,
            action=AuditAction.CHECKOUT_FORCED_UNPRINTED,
            entity_type="session",
            entity_id=session.id,
            staff_id=staff.id if staff else None,
            detail=(
                f"invoice_id={invoice.id}; "
                f"print_status={invoice.print_status.value}; "
                f"reason={override_reason}"
            ),
        )


async def _maybe_release_held_seat(
    db: AsyncSession,
    invoice: Invoice,
    *,
    staff: Staff | None = None,
) -> bool:
    """Release a held seat when the gate is on and the invoice is now PRINTED.

    Returns True if a release happened. No-op (False) when the gate is off,
    the invoice is not PRINTED, or the seat is not actually held (a COMPLETED
    session whose seat is still IN_USE). Used by mark-printed, reprint, and the
    scheduler auto-release hook.
    """
    if not get_flag("require_print_before_release"):
        return False
    if invoice.print_status != InvoicePrintStatus.PRINTED:
        return False
    session = await session_repo.get_by_id(db, invoice.session_id)
    if session is None or session.status != SessionStatus.COMPLETED:
        return False
    seat = await seat_repo.get_by_id(db, session.seat_id)
    if seat is None or seat.status != SeatStatus.IN_USE:
        return False
    await _release_held_seat(db, session, invoice, staff=staff)
    return True


async def checkout_session(
    db: AsyncSession,
    session_id: str,
    payment_method: PaymentMethod,
    staff: Staff | None = None,
    override_reason: str | None = None,
) -> Invoice:
    """Complete a gaming session and return the generated invoice.

    Steps:
    1.  Load + validate session (must be ACTIVE or PAUSED).
    2.  Compute elapsed time adjusted for pauses.
    3.  Build LockedRate and calculate time charge.
    4.  Compute total (POS items are stub; Feature 3.1.4).
    5.  Create Invoice in DB.
    6.  Update session -> COMPLETED, ended_at = now.
    7.  If ``require_print_before_release`` is ON: hold the seat IN_USE, await
        the first thermal print attempt, and release only when print_status
        becomes PRINTED (all releases go through ``_release_held_seat``).
        Otherwise release immediately and print fire-and-forget.
    8.  Broadcast seat_updated to dashboards.
    9.  Send SHOW_OVERLAY to agent.
    10. Audit log entry: CHECKOUT.
    11. Return Invoice (with refreshed print_status).
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

    # 3d. Calculate promotion discount (FR-PROMO-004)
    promotion_discount_paise: int = 0
    applied_promotion_name: str | None = None
    if session_obj.promotion_id:
        from backend.repositories import promotion_repo
        from backend.services.promotion_service import PromotionService

        promo = await promotion_repo.get_by_id(db, session_obj.promotion_id)
        if promo:
            promotion_discount_paise = (
                await PromotionService.calculate_promotion_discount(
                    db,
                    promo,
                    time_charge_paise=time_charge,
                    session_duration_minutes=int(elapsed / 60),
                    locked_rate_paise=session_obj.locked_rate_paise,
                    locked_pricing_model=session_obj.locked_pricing_model,
                )
            )
            applied_promotion_name = promo.name
            logger.info(
                "Applied promotion %s (%s) discount: %d paise",
                promo.name,
                promo.id,
                promotion_discount_paise,
            )

    # 4. Compute total (POS items summing)
    pos_items = await pos_repo.list_by_session(db, session_obj.id)
    pos_total_paise = sum(item.unit_price_paise * item.quantity for item in pos_items)
    discount_paise = session_obj.discount_paise or 0
    # Use session discount as fallback if no promotion; else use promo discount
    effective_discount = max(discount_paise, promotion_discount_paise)
    total_paise = max(0, time_charge + pos_total_paise - effective_discount)

    # 5. Create Invoice with package credit
    invoice = await invoice_repo.create(
        db,
        session_id=session_obj.id,
        member_id=session_obj.member_id,
        shift_id=session_obj.shift_id,
        time_charge_paise=time_charge,
        package_credit_used_paise=package_credit_paise,
        discount_paise=effective_discount,
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
    for pos_item in pos_items:
        menu_item = await inventory_repo.get_by_id(db, pos_item.menu_item_id)
        desc = menu_item.name if menu_item else f"POS Item {pos_item.menu_item_id}"
        await invoice_repo.create_line_item(
            db,
            invoice_id=invoice.id,
            type=InvoiceLineItemType.POS_ITEM,
            description=desc,
            quantity=pos_item.quantity,
            unit_price_paise=pos_item.unit_price_paise,
            total_paise=pos_item.unit_price_paise * pos_item.quantity,
        )
    if effective_discount > 0:
        discount_desc = (
            f"Promotion: {applied_promotion_name}"
            if applied_promotion_name
            else "Session discount"
        )
        await invoice_repo.create_line_item(
            db,
            invoice_id=invoice.id,
            type=InvoiceLineItemType.DISCOUNT,
            description=discount_desc,
            quantity=1,
            unit_price_paise=effective_discount,
            total_paise=effective_discount,
        )

    # 6. Update session -> COMPLETED
    session_obj.status = SessionStatus.COMPLETED
    session_obj.ended_at = datetime.now(UTC)
    await session_repo.update(db, session_obj)

    # 7. Load seat; decide gate hold vs. immediate release.
    seat = await seat_repo.get_by_id(db, session_obj.seat_id)
    gate_enabled = get_flag("require_print_before_release")
    seat_name = seat.name if seat else session_obj.seat_id

    # Build the receipt payload once (used by both gate-await and fire-and-forget).
    invoice_response = _build_invoice_response(invoice)

    if gate_enabled:
        # Hold the seat until the first thermal attempt succeeds.
        if seat:
            seat.status = SeatStatus.IN_USE
            await seat_repo.update(db, seat)
            try:
                await ws_manager.broadcast_to_dashboards(
                    "seat_updated",
                    {
                        "id": seat.id,
                        "name": seat.name,
                        "status": seat.status.value,
                        "current_session_id": session_obj.id,
                    },
                )
            except Exception:
                logger.warning(
                    "Failed to broadcast held seat_updated for %s",
                    seat.id,
                    exc_info=True,
                )

        # First attempt is awaited and bounded (~5s connect timeout inside escpos).
        try:
            config = get_config()
        except RuntimeError:
            config = None
        if config is not None:
            from backend.services.print_service import enqueue_and_track_print

            await enqueue_and_track_print(
                invoice.id,
                invoice_response,
                config.cafe_name,
                config,
                duration_seconds=elapsed,
                seat_name=seat_name,
            )
        else:
            logger.warning(
                "Config unavailable; cannot run first print attempt for %s",
                invoice.id,
            )

        # The print service committed print_status via its own session; read it back.
        refreshed = await invoice_repo.get_by_id(db, invoice.id)
        if refreshed is not None:
            invoice.print_status = refreshed.print_status

        if invoice.print_status == InvoicePrintStatus.PRINTED:
            await _release_held_seat(db, session_obj, invoice, staff=staff)
        # FAILED / SKIPPED / PENDING-without-config -> seat stays IN_USE (held).
    else:
        # Flag off: today's behaviour — release immediately, print fire-and-forget.
        if seat:
            seat.status = SeatStatus.AVAILABLE
            await seat_repo.update(db, seat)
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
        asyncio.create_task(_print_receipt(invoice_response, seat_name, elapsed))
        await _release_held_seat(db, session_obj, invoice, staff=staff)

    # 11. Audit CHECKOUT (always — the invoice was generated).
    await audit_service.log(
        db,
        action=AuditAction.CHECKOUT,
        entity_type="session",
        entity_id=session_obj.id,
        staff_id=staff.id if staff else None,
        detail=f"total_paise={total_paise}",
    )

    # 12. Return Invoice (with the refreshed print_status).
    await db.refresh(invoice)
    return invoice


async def force_close_unprinted(
    db: AsyncSession,
    session_id: str,
    pin: str,
    override_reason: str,
    staff: Staff,
) -> Invoice:
    """Force-release a held (unprinted) checkout after re-verifying the PIN.

    Preconditions (raise HTTPException):
      * PIN must verify against ``staff.pin_hash`` (403)
      * session must exist (404)
      * session.status == COMPLETED and seat still IN_USE (409)

    Releases the seat via the shared helper and audits
    CHECKOUT_FORCED_UNPRINTED. The invoice stays FAILED (intentionally unprinted).
    """
    if not verify_pin(pin, staff.pin_hash):
        raise HTTPException(status_code=403, detail="Invalid PIN")

    session = await session_repo.get_by_id(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=409, detail="Session is not in a held checkout state"
        )
    seat = await seat_repo.get_by_id(db, session.seat_id)
    if seat is None or seat.status != SeatStatus.IN_USE:
        raise HTTPException(
            status_code=409, detail="Seat is not held (already released)"
        )

    invoices = await invoice_repo.get_by_session(db, session.id)
    invoice = None
    if invoices:
        invoice = sorted(invoices, key=lambda i: i.created_at)[-1]
    if invoice is None:
        invoice = Invoice(
            session_id=session.id,
            payment_method=PaymentMethod.CASH,
            print_status=InvoicePrintStatus.FAILED,
        )
        db.add(invoice)
        await db.flush()

    await _release_held_seat(
        db, session, invoice, staff=staff, override_reason=override_reason
    )
    return invoice
