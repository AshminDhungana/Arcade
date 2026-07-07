"""Print service — formats and dispatches receipts to ESC/POS printers.

Prints receipts asynchronously (never blocks the checkout response).
Failures are logged as warnings but never raised.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from backend.models._enums import InvoiceLineItemType
from backend.schemas.invoice import InvoiceResponse

if TYPE_CHECKING:
    from backend.core.config import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Money formatting
# ---------------------------------------------------------------------------


def format_money(paise: int) -> str:
    """Convert paise to display string "Rs. X.XX".

    Args:
        paise: Amount in paise (integer 1/100 rupee).

    Returns:
        Formatted string, e.g. "Rs. 12.34".
    """
    rupees = paise // 100
    paise_remainder = paise % 100
    return f"Rs. {rupees}.{paise_remainder:02d}"


# ---------------------------------------------------------------------------
# Receipt formatting
# ---------------------------------------------------------------------------


def _format_receipt(
    invoice: InvoiceResponse,
    cafe_name: str,
    *,
    duration_seconds: int = 0,
    seat_name: str = "",
) -> list[str]:
    """Build a plain-text receipt suitable for a 32-column thermal printer.

    Args:
        invoice: Populated InvoiceResponse with line_items.
        cafe_name: Name of the cafe (from config).
        duration_seconds: Elapsed session duration in seconds, for display.
        seat_name: Name of the seat, for display.

    Returns:
        List of receipt lines.
    """
    lines: list[str] = []
    width = 32

    # --- Header -----------------------------------------------------------
    lines.append(cafe_name.center(width))
    lines.append("=" * width)

    # Seat / Session info
    if seat_name:
        lines.append(f"Seat: {seat_name}".ljust(width))
    date_str = invoice.created_at.strftime("%Y-%m-%d %H:%M")
    lines.append(f"Date: {date_str}".ljust(width))

    if duration_seconds > 0:
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        lines.append(f"Duration: {duration_str}".ljust(width))

    lines.append("-" * width)

    # --- Line items -------------------------------------------------------
    if invoice.line_items:
        for item in invoice.line_items:
            desc = item.description[:22].ljust(22)
            price = format_money(item.total_paise).rjust(10)
            lines.append(f"{desc}{price}")
        lines.append("-" * width)

    # --- Totals -----------------------------------------------------------
    time_charge = sum(
        li.total_paise
        for li in (invoice.line_items or [])
        if li.type == InvoiceLineItemType.TIME_CHARGE
    )
    discount = invoice.discount_paise or 0
    total = invoice.total_paise or 0

    if time_charge > 0:
        lines.append(f"Time: {format_money(time_charge).rjust(26)}")
    if discount > 0:
        lines.append(f"Disc: -{format_money(discount).rjust(24)}")

    lines.append("=" * width)
    lines.append(f"TOTAL:  {format_money(total).rjust(26)}")
    _payment = invoice.payment_method.value if invoice.payment_method else "CASH"
    lines.append(f"Paid:   {_payment.rjust(26)}")
    lines.append("-" * width)
    lines.append("Thank you!".center(width))

    return lines


# ---------------------------------------------------------------------------
# Printer dispatch
# ---------------------------------------------------------------------------


def _get_printer(config: Settings) -> Any:
    """Return an ESC/POS printer instance based on config.

    Args:
        config: Runtime Settings from core.config.

    Returns:
        Printer object with ``.text()``, ``.cut()``, ``.close()`` methods.
    """
    printer_type = config.printer_type
    if printer_type == "usb":
        from escpos.printer import Usb

        try:
            vendor = int(config.printer_usb_vendor or "0x04b8", 16)
            product = int(config.printer_usb_product or "0x0202", 16)
            return Usb(vendor, product)
        except RuntimeError:
            logger.warning("USB printer unavailable, falling back to dummy")
            return _DummyPrinter()
    if printer_type == "network":
        from escpos.printer import Network

        try:
            return Network("127.0.0.1", 9100)
        except RuntimeError:
            logger.warning("Network printer unavailable, falling back to dummy")
            return _DummyPrinter()

    logger.warning("Unsupported printer_type: %s, defaulting to dummy", printer_type)
    return _DummyPrinter()


def _run_escpos(printer: Any, lines: list[str]) -> None:
    """Run ESC/POS print commands (blocking).

    This function is intended to be called inside an executor so it does
    not block the event loop.
    """
    for line in lines:
        printer.text(line + "\n")
    printer.cut()
    printer.close()


class _DummyPrinter:
    """Fallback printer that logs instead of printing (for CI / missing hardware)."""

    def text(self, text: str) -> None:
        logger.debug("[DUMMY_PRINTER] %s", text.rstrip("\n"))

    def cut(self) -> None:
        logger.debug("[DUMMY_PRINTER] ---cut---")

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def print_receipt(
    invoice: InvoiceResponse,
    cafe_name: str,
    config: Settings,
    *,
    duration_seconds: int = 0,
    seat_name: str = "",
) -> None:
    """Print a receipt asynchronously — never blocks the caller.

    On any failure, logs a warning and returns without raising.

    Args:
        invoice: Populated InvoiceResponse with line_items.
        cafe_name: Name of the cafe.
        config: Runtime Settings from core.config.
        duration_seconds: Elapsed session duration in seconds, for receipt display.
        seat_name: Name of the seat, for display.
    """
    try:
        receipt_lines = _format_receipt(
            invoice, cafe_name, duration_seconds=duration_seconds, seat_name=seat_name
        )
        printer = _get_printer(config)
        # Run the blocking ESC/POS I/O in a thread so the event loop stays free
        await asyncio.to_thread(_run_escpos, printer, receipt_lines)
        logger.info("Receipt printed for invoice %s", invoice.id)
    except Exception:
        logger.warning(
            "Failed to print receipt for invoice %s", invoice.id, exc_info=True
        )
