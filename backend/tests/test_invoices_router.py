"""Integration tests for the invoices API router."""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from backend.api.deps import get_current_staff
from backend.main import app

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_staff(role="ADMIN"):
    """Return a plain object that mimics a Staff model."""
    from backend.models._enums import StaffRole

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock Admin"
        is_active = True
        token_version = 0

    obj = _MockStaff()
    if isinstance(role, str):
        obj.role = StaffRole(role)
    else:
        obj.role = role
    return obj


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a TestClient that bypasses auth."""
    mock_staff = _make_mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_current_staff, None)


# ---------------------------------------------------------------------------
# GET /api/invoices/{id}
# ---------------------------------------------------------------------------


def test_get_invoice_not_found(client: TestClient) -> None:
    """GET /api/invoices/{id} for a missing invoice returns 404."""
    resp = client.get("/api/invoices/non-existent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/invoices/{id}/pdf
# ---------------------------------------------------------------------------


def test_get_invoice_pdf_not_found(client: TestClient) -> None:
    """GET /api/invoices/{id}/pdf for a missing invoice returns 404."""
    resp = client.get("/api/invoices/non-existent-id/pdf")
    assert resp.status_code == 404


@pytest.fixture
async def async_client() -> Iterator[AsyncClient]:
    """Yield an AsyncClient bound to the real app with auth bypassed."""
    mock_staff = _make_mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(get_current_staff, None)


async def test_get_invoice_pdf_renders_receipt_fields(
    async_client: AsyncClient,
) -> None:
    """E.6: PDF/browser-print fallback renders the same receipt fields.

    An invoice with time charge + POS line items renders to print-friendly
    HTML containing cafe name, date, line items, totals and payment method —
    the same fields as the thermal receipt (E.5).
    """
    from datetime import UTC, datetime, timedelta

    from backend.core.database import AsyncSessionLocal
    from backend.models._enums import (
        InvoiceLineItemType,
        PaymentMethod,
        PricingModel,
    )
    from backend.repositories import invoice_repo, seat_repo, session_repo, zone_repo

    async with AsyncSessionLocal() as db:
        zone = await zone_repo.create(
            db,
            name="TestZone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=3000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
        sess = await session_repo.create(
            db,
            seat_id=seat.id,
            started_at=datetime.now(UTC) - timedelta(minutes=10),
            locked_rate_paise=100,
            locked_pricing_model=PricingModel.PER_MINUTE,
        )
        invoice = await invoice_repo.create(
            db,
            session_id=sess.id,
            time_charge_paise=1000,
            pos_total_paise=300,
            total_paise=1300,
            payment_method=PaymentMethod.CASH,
        )
        await invoice_repo.create_line_item(
            db,
            invoice_id=invoice.id,
            type=InvoiceLineItemType.TIME_CHARGE,
            description="Time charge",
            quantity=10,
            unit_price_paise=100,
            total_paise=1000,
        )
        await invoice_repo.create_line_item(
            db,
            invoice_id=invoice.id,
            type=InvoiceLineItemType.POS_ITEM,
            description="Cold Coke",
            quantity=2,
            unit_price_paise=150,
            total_paise=300,
        )
        await db.commit()
        invoice_id = invoice.id
        seat_id = seat.id
        zone_id = zone.id

    resp = await async_client.get(f"/api/invoices/{invoice_id}/pdf")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html = resp.text

    # Cafe name (default "Arcade" in the test config), date, items, totals
    assert "Arcade" in html
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", html) is not None
    assert "Time charge:" in html
    assert "Rs. 10.00" in html
    assert "Cold Coke" in html
    assert "TOTAL:" in html
    assert "Rs. 13.00" in html
    assert "Paid by:" in html
    assert "CASH" in html
    # The fallback path triggers the browser's own print dialog
    assert "window.print()" in html

    # Clean up the seeded rows in FK order: other tests share this DB and
    # issue bare `DELETE FROM seats` (e.g. test_seat_status_integration),
    # which fails while orphan sessions/invoices still reference them.
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM invoice_line_items WHERE invoice_id = :iid"),
            {"iid": invoice_id},
        )
        await db.execute(
            text("DELETE FROM invoices WHERE id = :iid"), {"iid": invoice_id}
        )
        await db.execute(
            text("DELETE FROM sessions WHERE seat_id = :sid"), {"sid": seat_id}
        )
        await db.execute(text("DELETE FROM seats WHERE id = :sid"), {"sid": seat_id})
        await db.execute(text("DELETE FROM zones WHERE id = :zid"), {"zid": zone_id})
        await db.commit()
