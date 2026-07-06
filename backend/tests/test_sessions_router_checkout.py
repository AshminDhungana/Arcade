"""Integration tests for the checkout route (Feature 3.1.2)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_current_staff
from backend.main import app

# ---------------------------------------------------------------------------
# Helpers
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
def client():
    """Yield a TestClient that bypasses auth and runs lifespan."""
    mock_staff = _make_mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_current_staff, None)


# ---------------------------------------------------------------------------
# POST /api/sessions/{id}/checkout
# ---------------------------------------------------------------------------


def test_checkout_not_found(client: TestClient) -> None:
    """Checkout a non-existent session returns 404."""
    resp = client.post(
        "/api/sessions/non-existent-id/checkout", json={"payment_method": "CASH"}
    )
    assert resp.status_code == 404


def test_checkout_invalid_method(client: TestClient) -> None:
    """Checkout with missing payment_method returns 422."""
    resp = client.post("/api/sessions/some-id/checkout", json={})
    assert resp.status_code == 422
