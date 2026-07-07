"""Tests for the print service."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.models._enums import PaymentMethod
from backend.schemas.invoice import InvoiceLineItemResponse, InvoiceResponse
from backend.services.print_service import format_money, print_receipt

# ---------------------------------------------------------------------------
# format_money
# ---------------------------------------------------------------------------


class TestFormatMoney:
    def test_zero_paise(self) -> None:
        assert format_money(0) == "Rs. 0.00"

    def test_one_hundred_paise(self) -> None:
        assert format_money(100) == "Rs. 1.00"

    def test_fractional_paise(self) -> None:
        assert format_money(1234) == "Rs. 12.34"

    def test_large_amount(self) -> None:
        assert format_money(99999) == "Rs. 999.99"

    def test_round_hundreds(self) -> None:
        assert format_money(1500) == "Rs. 15.00"
        assert format_money(500) == "Rs. 5.00"


# ---------------------------------------------------------------------------
# print_receipt
# ---------------------------------------------------------------------------


class TestPrintReceipt:
    @pytest.mark.anyio
    async def test_print_receipt_non_blocking(self) -> None:
        """A slow printer (2s) must not block for more than 100ms.

        The function should return control within 100ms, with the actual
        ESC/POS I/O running in a background thread executor.
        """

        class SlowPrinter:
            def text(self, text: str) -> None:
                time.sleep(2.0)

            def cut(self) -> None:
                pass

            def close(self) -> None:
                pass

        from backend.services import print_service as ps

        mock_config = MagicMock()
        mock_config.cafe_name = "Test Cafe"
        mock_config.printer_type = "usb"
        mock_config.printer_usb_vendor = "0x04b8"
        mock_config.printer_usb_product = "0x0202"

        now = datetime.now(UTC)
        mock_invoice = InvoiceResponse(
            id="inv-1",
            session_id="sess-1",
            payment_method=PaymentMethod.CASH,
            line_items=[],
            created_at=now,
        )

        with patch.object(ps, "_get_printer", return_value=SlowPrinter()):
            start = time.monotonic()
            task = asyncio.create_task(
                print_receipt(mock_invoice, "Test", mock_config),
            )
            # Give the event loop a chance to run the task
            await asyncio.sleep(0.01)
            elapsed = time.monotonic() - start

            assert elapsed < 0.1, f"Print blocked for {elapsed:.3f}s, expected <0.1s"
            # Clean up
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.anyio
    async def test_print_receipt_failure_logs_warning(self, caplog) -> None:
        """Printer failure must log a warning, never raise."""
        from backend.services import print_service as ps

        mock_config = MagicMock()
        mock_config.printer_type = "usb"
        mock_config.printer_usb_vendor = "0x04b8"
        mock_config.printer_usb_product = "0x0202"

        def _bad_printer(config):
            raise RuntimeError("Printer on fire")

        with patch.object(
            ps, "_get_printer", side_effect=RuntimeError("Printer on fire")
        ):
            now = datetime.now(UTC)
            mock_invoice = InvoiceResponse(
                id="inv-2",
                session_id="sess-2",
                payment_method=PaymentMethod.CASH,
                line_items=[],
                created_at=now,
            )

            # Should not raise
            await print_receipt(mock_invoice, "Test", mock_config)

        # Should have logged a warning
        assert "Failed to print" in caplog.text

    def test_format_receipt_output(self) -> None:
        """Verify the receipt text contains expected content."""
        from backend.models._enums import InvoiceLineItemType
        from backend.services.print_service import _format_receipt

        now = datetime.now(UTC)
        invoice = InvoiceResponse(
            id="inv-3",
            session_id="sess-3",
            payment_method=PaymentMethod.CARD,
            line_items=[
                InvoiceLineItemResponse(
                    id="li-1",
                    invoice_id="inv-3",
                    type=InvoiceLineItemType.TIME_CHARGE,
                    description="Time charge",
                    quantity=1,
                    unit_price_paise=500,
                    total_paise=500,
                ),
                InvoiceLineItemResponse(
                    id="li-2",
                    invoice_id="inv-3",
                    type=InvoiceLineItemType.POS_ITEM,
                    description="Cola",
                    quantity=2,
                    unit_price_paise=100,
                    total_paise=200,
                ),
            ],
            time_charge_paise=500,
            discount_paise=50,
            total_paise=650,
            created_at=now,
        )

        lines = _format_receipt(invoice, "Test Cafe", duration_seconds=3660)
        text = "\n".join(lines)

        assert "Test Cafe" in text
        assert "Time charge" in text
        assert "Cola" in text
        assert "Rs. 6.50" in text  # total
        assert "CARD" in text
