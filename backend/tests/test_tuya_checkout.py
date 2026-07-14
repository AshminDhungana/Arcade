"""Integration test: checkout_session triggers Tuya console power-off."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models import PricingModel
from backend.models._enums import (
    PaymentMethod,
    SeatStatus,
    SessionStatus,
)
from backend.services import billing_service


def _fake_session() -> SimpleNamespace:
    return SimpleNamespace(
        id="S1",
        seat_id="seat-1",
        status=SessionStatus.ACTIVE,
        member_id=None,
        discount_paise=0,
        package_entitlement_id=None,
        promotion_id=None,
        locked_rate_paise=5,
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id=None,
    )


def _fake_seat() -> SimpleNamespace:
    return SimpleNamespace(id="seat-1", name="PC-1", status=SeatStatus.AVAILABLE)


def _fake_invoice() -> SimpleNamespace:
    return SimpleNamespace(
        id="INV-1",
        session_id="S1",
        member_id=None,
        shift_id=None,
        time_charge_paise=0,
        package_credit_used_paise=0,
        discount_paise=0,
        pos_total_paise=0,
        total_paise=0,
        payment_method=PaymentMethod.CASH,
        created_at=None,
    )


async def test_checkout_triggers_tuya_power_off() -> None:
    """Checkout powers the console off, passing (db, seat_id)."""
    db = AsyncMock()
    mock_tuya = AsyncMock()
    fake_session = _fake_session()
    with (
        patch.object(
            billing_service, "_compute_elapsed_seconds", MagicMock(return_value=60)
        ),
        patch.object(
            billing_service, "calculate_time_charge", MagicMock(return_value=0)
        ),
        patch.object(
            billing_service.invoice_repo,
            "create",
            new=AsyncMock(return_value=_fake_invoice()),
        ),
        patch.object(
            billing_service.invoice_repo,
            "create_line_item",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            billing_service.pos_repo,
            "list_by_session",
            new=AsyncMock(return_value=[]),
        ),
        patch.object(
            billing_service.session_repo,
            "get_by_id",
            new=AsyncMock(return_value=fake_session),
        ),
        patch.object(billing_service.session_repo, "update", new=AsyncMock()),
        patch.object(
            billing_service.seat_repo,
            "get_by_id",
            new=AsyncMock(return_value=_fake_seat()),
        ),
        patch.object(billing_service.seat_repo, "update", new=AsyncMock()),
        patch.object(
            billing_service.ws_manager, "broadcast_to_dashboards", new=AsyncMock()
        ),
        patch.object(billing_service.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(billing_service.audit_service, "log", new=AsyncMock()),
        patch.object(billing_service, "_print_receipt", new=AsyncMock()),
        patch(
            "backend.schemas.invoice.InvoiceResponse",
            lambda **kw: SimpleNamespace(**kw),
        ),
        patch("backend.services.tuya_service", new=mock_tuya),
    ):
        await billing_service.checkout_session(db, "S1", PaymentMethod.CASH, staff=None)

    mock_tuya.power_off.assert_awaited_once()
    assert mock_tuya.power_off.call_args.args == (db, "seat-1")


async def test_checkout_continues_when_tuya_raises() -> None:
    """If Tuya raises, checkout still completes (failure is non-fatal)."""
    db = AsyncMock()
    mock_tuya = AsyncMock()
    mock_tuya.power_off.side_effect = RuntimeError("plug unreachable")
    fake_session = _fake_session()
    with (
        patch.object(
            billing_service, "_compute_elapsed_seconds", MagicMock(return_value=60)
        ),
        patch.object(
            billing_service, "calculate_time_charge", MagicMock(return_value=0)
        ),
        patch.object(
            billing_service.invoice_repo,
            "create",
            new=AsyncMock(return_value=_fake_invoice()),
        ),
        patch.object(
            billing_service.invoice_repo,
            "create_line_item",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            billing_service.pos_repo,
            "list_by_session",
            new=AsyncMock(return_value=[]),
        ),
        patch.object(
            billing_service.session_repo,
            "get_by_id",
            new=AsyncMock(return_value=fake_session),
        ),
        patch.object(billing_service.session_repo, "update", new=AsyncMock()),
        patch.object(
            billing_service.seat_repo,
            "get_by_id",
            new=AsyncMock(return_value=_fake_seat()),
        ),
        patch.object(billing_service.seat_repo, "update", new=AsyncMock()),
        patch.object(
            billing_service.ws_manager, "broadcast_to_dashboards", new=AsyncMock()
        ),
        patch.object(billing_service.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(billing_service.audit_service, "log", new=AsyncMock()),
        patch.object(billing_service, "_print_receipt", new=AsyncMock()),
        patch(
            "backend.schemas.invoice.InvoiceResponse",
            lambda **kw: SimpleNamespace(**kw),
        ),
        patch("backend.services.tuya_service", new=mock_tuya),
    ):
        # Must NOT raise.
        await billing_service.checkout_session(db, "S1", PaymentMethod.CASH, staff=None)
