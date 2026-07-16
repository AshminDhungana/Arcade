"""Tests for Invoice.print_status plumbing (model + schema)."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.models._enums import InvoicePrintStatus, PaymentMethod
from backend.schemas.invoice import InvoiceResponse


def test_invoice_response_print_status_defaults_pending() -> None:
    now = datetime.now(UTC)
    resp = InvoiceResponse(
        id="inv-1",
        session_id="sess-1",
        payment_method=PaymentMethod.CASH,
        line_items=[],
        created_at=now,
    )
    assert resp.print_status == InvoicePrintStatus.PENDING


def test_invoice_response_print_status_round_trips_value() -> None:
    now = datetime.now(UTC)
    resp = InvoiceResponse(
        id="inv-2",
        session_id="sess-2",
        payment_method=PaymentMethod.CARD,
        print_status=InvoicePrintStatus.FAILED,
        line_items=[],
        created_at=now,
    )
    assert resp.print_status == InvoicePrintStatus.FAILED
