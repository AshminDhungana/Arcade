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


# ---------------------------------------------------------------------------
# Print-status tracking / outbox (Appends to test_print.py)
# ---------------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.core.database import Base  # noqa: E402
from backend.models._enums import InvoicePrintStatus  # noqa: E402
from backend.repositories import invoice_repo, print_job_repo  # noqa: E402, F401
from backend.services import print_service as ps  # noqa: E402

_CASH = __import__(
    "backend.models._enums", fromlist=["PaymentMethod"]
).PaymentMethod.CASH  # noqa: E501

# StaticPool is required so the in-memory ":memory:" database is shared across
# the test's session and the session that ``enqueue_and_track_print`` opens for
# itself — otherwise each checked-out connection gets its own isolated DB and
# the background commit is never visible to the assertions below.
_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
_MAKER = async_sessionmaker(_ENGINE, expire_on_commit=False)
_INITED = False


async def _ensure_tables() -> None:
    global _INITED
    if not _INITED:
        async with _ENGINE.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _INITED = True


async def _in_memory_session():
    await _ensure_tables()
    return _MAKER()


def _sessionmaker():
    # Same engine; enqueue_and_track_print opens its own session from this maker.
    return _MAKER


class _DummyOKPrinter:
    def text(self, text: str) -> None:
        pass

    def cut(self) -> None:
        pass

    def close(self) -> None:
        pass


def _make_invoice_response(inv_id: str):
    return InvoiceResponse(
        id=inv_id,
        session_id="sess",
        payment_method=PaymentMethod.CASH,
        line_items=[],
        created_at=datetime.now(UTC),
    )


def _make_config():
    cfg = MagicMock()
    cfg.cafe_name = "Test"
    cfg.printer_type = "usb"
    cfg.printer_usb_vendor = "0x04b8"
    cfg.printer_usb_product = "0x0202"
    return cfg


def _resp_for(inv):
    from backend.models._enums import InvoiceLineItemType
    from backend.schemas.invoice import InvoiceLineItemResponse, InvoiceResponse

    return InvoiceResponse(
        id=inv.id,
        session_id=inv.session_id,
        payment_method=inv.payment_method or PaymentMethod.CASH,
        line_items=[
            InvoiceLineItemResponse(
                id="li-x",
                invoice_id=inv.id,
                type=InvoiceLineItemType.TIME_CHARGE,
                description="Time charge",
                quantity=1,
                unit_price_paise=inv.total_paise,
                total_paise=inv.total_paise,
            )
        ],
        created_at=datetime.now(UTC),
    )


class TestPrintStatusTracking:
    @pytest.mark.anyio
    async def test_print_receipt_returns_bool(self) -> None:
        cfg = _make_config()
        inv = _make_invoice_response("inv-bool")
        with patch.object(ps, "_get_printer", return_value=_DummyOKPrinter()):
            assert await ps.print_receipt(inv, "Test", cfg) is True
        with patch.object(ps, "_get_printer", side_effect=RuntimeError("boom")):
            assert await ps.print_receipt(inv, "Test", cfg) is False

    @pytest.mark.anyio
    async def test_next_retry_delay_backoff(self) -> None:
        assert ps._next_retry_delay(1) == timedelta(minutes=2)
        assert ps._next_retry_delay(3) == timedelta(minutes=8)
        # capped at 30 minutes
        assert ps._next_retry_delay(10) == timedelta(minutes=30)

    @pytest.mark.anyio
    async def test_enqueue_tracks_printed(self) -> None:
        db = await _in_memory_session()
        inv = await invoice_repo.create(
            db, session_id="s1", payment_method=_CASH, total_paise=100
        )
        await db.commit()
        cfg = _make_config()
        with patch.object(ps, "_get_printer", return_value=_DummyOKPrinter()):
            await ps.enqueue_and_track_print(
                inv.id, _resp_for(inv), "Test", cfg, session_factory=_sessionmaker()
            )
        await db.commit()
        # The outbox session enqueue_and_track_print opened committed its own
        # changes; read via a fresh session so we observe the persisted outcome
        # rather than the original (PENDING) instance cached in `db`.
        async with _MAKER() as db2:
            reloaded = await invoice_repo.get_by_id(db2, inv.id)
            assert reloaded.print_status == InvoicePrintStatus.PRINTED
            assert await ps.print_job_repo.get_by_invoice(db2, inv.id) is None

    @pytest.mark.anyio
    async def test_enqueue_tracks_failed_and_enqueues_job(self) -> None:
        db = await _in_memory_session()
        inv = await invoice_repo.create(
            db, session_id="s2", payment_method=_CASH, total_paise=200
        )
        await db.commit()
        cfg = _make_config()
        with patch.object(ps, "_get_printer", side_effect=RuntimeError("printer dead")):
            await ps.enqueue_and_track_print(
                inv.id, _resp_for(inv), "Test", cfg, session_factory=_sessionmaker()
            )
        await db.commit()
        # Read via a fresh session to observe the outbox session's committed
        # FAILED outcome rather than the cached (PENDING) instance in `db`.
        async with _MAKER() as db2:
            reloaded = await invoice_repo.get_by_id(db2, inv.id)
            assert reloaded.print_status == InvoicePrintStatus.FAILED
            job = await ps.print_job_repo.get_by_invoice(db2, inv.id)
        assert job is not None
        assert job.attempts == 1
        assert job.last_error == "printer dead"
        assert job.next_retry_at is not None

    @pytest.mark.anyio
    async def test_retry_due_print_jobs_succeeds(self) -> None:
        db = await _in_memory_session()
        inv = await invoice_repo.create(
            db, session_id="s3", payment_method=_CASH, total_paise=300
        )
        await ps.print_job_repo.create(
            db,
            invoice_id=inv.id,
            attempts=1,
            next_retry_at=datetime.now(UTC) - timedelta(minutes=1),
            last_error="x",
        )
        await db.commit()
        with patch.object(ps, "_get_printer", return_value=_DummyOKPrinter()):
            retried = await ps.retry_due_print_jobs(db)
        await db.commit()
        assert retried == 1
        reloaded = await invoice_repo.get_by_id(db, inv.id)
        assert reloaded.print_status == InvoicePrintStatus.PRINTED
        assert await ps.print_job_repo.get_by_invoice(db, inv.id) is None

    @pytest.mark.anyio
    async def test_mark_print_skipped_removes_job(self) -> None:
        db = await _in_memory_session()
        inv = await invoice_repo.create(
            db, session_id="s4", payment_method=_CASH, total_paise=400
        )
        await ps.print_job_repo.create(
            db,
            invoice_id=inv.id,
            attempts=2,
            next_retry_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        await db.commit()
        await ps.mark_print_skipped(db, inv.id)
        await db.commit()
        reloaded = await invoice_repo.get_by_id(db, inv.id)
        assert reloaded.print_status == InvoicePrintStatus.SKIPPED
        assert await ps.print_job_repo.get_by_invoice(db, inv.id) is None
