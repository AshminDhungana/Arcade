"""Print service — formats and dispatches receipts to ESC/POS printers.

Prints receipts asynchronously (never blocks the checkout response).
Failures are logged as warnings but never raised.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_config
from backend.core.database import AsyncSessionLocal
from backend.models._enums import InvoiceLineItemType, InvoicePrintStatus
from backend.models.invoice import Invoice
from backend.repositories import invoice_repo, print_job_repo
from backend.schemas.invoice import InvoiceLineItemResponse, InvoiceResponse

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
# Printer URI parsing
# ---------------------------------------------------------------------------


def _parse_printer_uri(uri: str) -> dict[str, Any]:
    """Parse a printer URI into components.

    Supported schemes:
    - usb://<device-path> or usb://<vendor>:<product>
    - socket://<host>:<port>
    - ipp://<host>:<port>/<path>
    - http://<host>:<port>/<path>
    - https://<host>:<port>/<path>
    - lpd://<host>:<port>/<queue>

    Returns a dict with: scheme, host, port, path, vendor, product
    """
    # Handle USB URIs specially: urlparse treats vendor:product as host:port
    if uri.startswith("usb://"):
        rest = uri[6:]  # Remove "usb://"
        if ":" in rest and not rest.startswith(":"):
            # Format: usb://vendor:product
            parts = rest.split(":", 1)
            try:
                vendor = int(parts[0], 16)
                product = int(parts[1], 16)
                return {
                    "scheme": "usb",
                    "host": None,
                    "port": None,
                    "path": "",
                    "vendor": vendor,
                    "product": product,
                }
            except ValueError:
                pass
        # Format: usb://device-path
        return {
            "scheme": "usb",
            "host": None,
            "port": None,
            "path": rest,
            "vendor": None,
            "product": None,
        }

    # For network URIs, use urlparse
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()

    result: dict[str, Any] = {
        "scheme": scheme,
        "host": parsed.hostname,
        "port": parsed.port,
        "path": parsed.path.lstrip("/"),
        "vendor": None,
        "product": None,
    }

    # Default ports for network schemes
    if scheme in ("http", "https") and result["port"] is None:
        result["port"] = 80 if scheme == "http" else 443
    elif scheme == "ipp" and result["port"] is None:
        result["port"] = 631
    elif scheme == "lpd" and result["port"] is None:
        result["port"] = 515
    elif scheme == "socket" and result["port"] is None:
        result["port"] = 9100

    return result


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
    printer_uri = config.printer_uri

    # If printer_uri is provided, parse it and use for connection
    if printer_uri:
        parsed = _parse_printer_uri(printer_uri)
        scheme = parsed["scheme"]

        # USB printer with URI
        if scheme == "usb":
            from escpos.printer import Usb

            vendor = parsed["vendor"]
            product = parsed["product"]

            # Fall back to config values if not in URI
            if vendor is None:
                vendor = int(config.printer_usb_vendor or "0x04b8", 16)
            if product is None:
                product = int(config.printer_usb_product or "0x0202", 16)

            try:
                return Usb(vendor, product)
            except RuntimeError:
                logger.warning(
                    "USB printer unavailable (%s), falling back to dummy",
                    printer_uri,
                )
                return _DummyPrinter()

        # Network printer schemes
        if scheme in ("socket", "ipp", "http", "https", "lpd"):
            from escpos.printer import Network

            host = parsed["host"]
            port = parsed["port"]

            if host is None or port is None:
                logger.warning(
                    "Invalid network printer URI: %s, falling back to dummy",
                    printer_uri,
                )
                return _DummyPrinter()

            try:
                return Network(host, port)
            except RuntimeError:
                logger.warning(
                    "Network printer unavailable (%s), falling back to dummy",
                    printer_uri,
                )
                return _DummyPrinter()

        # Unknown scheme - fall back to legacy printer_type behavior
        logger.warning(
            "Unsupported printer URI scheme: %s, falling back to printer_type=%s",
            scheme,
            printer_type,
        )

    # No printer_uri provided - fall back to legacy behavior
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
) -> bool:
    """Print a receipt asynchronously — never blocks the caller.

    On any failure, logs a warning and returns ``False`` without raising.

    Args:
        invoice: Populated InvoiceResponse with line_items.
        cafe_name: Name of the cafe.
        config: Runtime Settings from core.config.
        duration_seconds: Elapsed session duration in seconds, for receipt display.
        seat_name: Name of the seat, for display.

    Returns:
        ``True`` if the receipt was printed, ``False`` on failure.
    """
    try:
        receipt_lines = _format_receipt(
            invoice, cafe_name, duration_seconds=duration_seconds, seat_name=seat_name
        )
        printer = _get_printer(config)
        # Run the blocking ESC/POS I/O in a thread so the event loop stays free
        await asyncio.to_thread(_run_escpos, printer, receipt_lines)
        logger.info("Receipt printed for invoice %s", invoice.id)
        return True
    except Exception:
        logger.warning(
            "Failed to print receipt for invoice %s", invoice.id, exc_info=True
        )
        return False


# ---------------------------------------------------------------------------
# Print-status tracking + outbox retry
# ---------------------------------------------------------------------------


MAX_PRINT_ATTEMPTS: int = 5


def _next_retry_delay(attempts_completed: int) -> timedelta:
    """Exponential backoff capped at 30 minutes.

    Args:
        attempts_completed: Number of print attempts already made.

    Returns:
        Delay before the next attempt.
    """
    return timedelta(minutes=min(2**attempts_completed, 30))


def _build_invoice_response(invoice: Invoice) -> InvoiceResponse:
    """Rebuild an :class:`InvoiceResponse` (with line items) from an ORM invoice."""
    # SQLite returns naive datetimes, but the schema requires tz-aware values.
    created_at = invoice.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return InvoiceResponse(
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
        print_status=invoice.print_status,
        created_at=created_at,
        line_items=[
            InvoiceLineItemResponse(
                id=li.id,
                invoice_id=li.invoice_id,
                type=li.type,
                description=li.description,
                quantity=li.quantity,
                unit_price_paise=li.unit_price_paise,
                total_paise=li.total_paise,
            )
            for li in (invoice.line_items or [])
        ],
    )


async def _print_receipt_core(
    invoice: InvoiceResponse,
    cafe_name: str,
    config: Settings,
    *,
    duration_seconds: int = 0,
    seat_name: str = "",
) -> tuple[bool, str | None]:
    """Print and return ``(success, error_message)``. Never raises."""
    try:
        receipt_lines = _format_receipt(
            invoice, cafe_name, duration_seconds=duration_seconds, seat_name=seat_name
        )
        printer = _get_printer(config)
        await asyncio.to_thread(_run_escpos, printer, receipt_lines)
        logger.info("Receipt printed for invoice %s", invoice.id)
        return True, None
    except Exception as exc:  # noqa: BLE001 — surface reason to the outbox
        logger.warning(
            "Failed to print receipt for invoice %s", invoice.id, exc_info=True
        )
        return False, str(exc)


async def _persist_outcome(
    db: AsyncSession,
    invoice_id: str,
    ok: bool,
    last_error: str | None,
) -> None:
    """Record the print outcome on the invoice and upsert/delete its job row."""
    inv = await invoice_repo.get_by_id(db, invoice_id)
    if inv is None:
        return
    if ok:
        inv.print_status = InvoicePrintStatus.PRINTED
        existing = await print_job_repo.get_by_invoice(db, invoice_id)
        if existing is not None:
            await print_job_repo.delete(db, existing)
        return

    inv.print_status = InvoicePrintStatus.FAILED
    now = datetime.now(UTC)
    existing = await print_job_repo.get_by_invoice(db, invoice_id)
    if existing is None:
        await print_job_repo.create(
            db,
            invoice_id=invoice_id,
            attempts=1,
            last_error=last_error,
            next_retry_at=now + _next_retry_delay(1),
        )
        return
    existing.attempts += 1
    existing.last_error = last_error
    if existing.attempts >= MAX_PRINT_ATTEMPTS:
        existing.next_retry_at = None  # give up; invoice stays FAILED
    else:
        existing.next_retry_at = now + _next_retry_delay(existing.attempts)
    await print_job_repo.update(db, existing)


async def enqueue_and_track_print(
    invoice_id: str,
    invoice: InvoiceResponse,
    cafe_name: str,
    config: Settings,
    *,
    duration_seconds: int = 0,
    seat_name: str = "",
    session_factory: Any = AsyncSessionLocal,
) -> None:
    """Print a receipt and persist the outcome + outbox job.

    Opens its own DB session (injectable for tests) so it is safe to call from
    ``asyncio.create_task`` after the request session has closed. On success the
    invoice is marked PRINTED and any job row removed; on failure it is marked
    FAILED and a job row is upserted for background retry.
    """
    try:
        ok, err = await _print_receipt_core(
            invoice,
            cafe_name,
            config,
            duration_seconds=duration_seconds,
            seat_name=seat_name,
        )
    except Exception as exc:  # noqa: BLE001 — never escape the fire-and-forget task
        logger.exception(
            "Unexpected error in print core for invoice %s; recording retry row",
            invoice_id,
        )
        await _ensure_retry_row(invoice_id, str(exc), session_factory)
        return

    try:
        async with session_factory() as db:
            await _persist_outcome(db, invoice_id, ok, err)
            await db.commit()
    except Exception as exc:  # noqa: BLE001 — never escape the fire-and-forget task
        logger.exception(
            "Failed to persist print outcome for invoice %s; "
            "recording a retryable outbox row",
            invoice_id,
        )
        await _ensure_retry_row(invoice_id, str(exc), session_factory)


async def _ensure_retry_row(invoice_id: str, error: str, session_factory: Any) -> None:
    """Best-effort: ensure a retryable ``PrintJob`` outbox row exists.

    Called when the primary persistence step fails so the invoice is never
    silently left at PENDING with no retry path. Opens a FRESH session from the
    injected ``session_factory`` (NOT ``AsyncSessionLocal`` directly) so it
    stays consistent with the in-memory factory used in tests. A double failure
    (the fallback itself raises) is only logged — it must never propagate out
    of the fire-and-forget task.
    """
    try:
        async with session_factory() as db:
            existing = await print_job_repo.get_by_invoice(db, invoice_id)
            if existing is None:
                await print_job_repo.create(
                    db,
                    invoice_id=invoice_id,
                    attempts=0,
                    last_error=error,
                    next_retry_at=datetime.now(UTC) + _next_retry_delay(0),
                )
            await db.commit()
    except Exception:  # noqa: BLE001 — double failure: log only
        logger.exception(
            "Failed to create fallback retry row for invoice %s", invoice_id
        )


async def mark_print_skipped(db: AsyncSession, invoice_id: str) -> None:
    """Mark an invoice as intentionally not printed (no retry)."""
    inv = await invoice_repo.get_by_id(db, invoice_id)
    if inv is None:
        return
    inv.print_status = InvoicePrintStatus.SKIPPED
    existing = await print_job_repo.get_by_invoice(db, invoice_id)
    if existing is not None:
        await print_job_repo.delete(db, existing)
    await db.flush()


async def retry_due_print_jobs(db: AsyncSession) -> list[str]:
    """Re-attempt all due print jobs. Flush-only; the caller commits.

    Returns the list of invoice IDs that were successfully printed this run
    (so the scheduler can auto-release any held seats).
    """
    now = datetime.now(UTC)
    jobs = await print_job_repo.list_due(db, now)
    printed: list[str] = []
    for job in jobs:
        inv = await invoice_repo.get_by_id(db, job.invoice_id)
        if inv is None:
            await print_job_repo.delete(db, job)
            continue
        config = get_config()
        response = _build_invoice_response(inv)
        ok, err = await _print_receipt_core(response, config.cafe_name, config)
        if ok:
            inv.print_status = InvoicePrintStatus.PRINTED
            await print_job_repo.delete(db, job)
            printed.append(inv.id)
        else:
            job.attempts += 1
            job.last_error = err
            if job.attempts >= MAX_PRINT_ATTEMPTS:
                job.next_retry_at = None
            else:
                job.next_retry_at = now + _next_retry_delay(job.attempts)
            await print_job_repo.update(db, job)
    return printed
