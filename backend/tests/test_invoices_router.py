"""Integration tests for the invoices API router."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

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
