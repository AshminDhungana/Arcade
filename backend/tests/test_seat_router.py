"""Integration tests for the Seat API router.

Uses :class:`fastapi.testclient.TestClient` with dependency overrides to
bypass JWT auth in favour of a mock staff object.
"""

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
    """Return a plain object that mimics a :class:`backend.models.staff.Staff`."""
    from backend.models._enums import StaffRole

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock Admin"
        is_active = True
        token_version = 0

    obj = _MockStaff()
    # Ensure role is an enum member for compatibility with role checkers
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
    """Yield a TestClient that bypasses auth and runs lifespan."""
    mock_staff = _make_mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_current_staff, None)


@pytest.fixture
def cashier_client() -> Iterator[TestClient]:
    """Yield a TestClient authenticated as a cashier (not admin)."""
    mock_staff = _make_mock_staff("CASHIER")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_current_staff, None)


# ---------------------------------------------------------------------------
# GET /api/seats
# ---------------------------------------------------------------------------


def test_list_seats_empty(client: TestClient) -> None:
    resp = client.get("/api/seats")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_seats_returns_list(client: TestClient) -> None:
    resp = client.get("/api/seats")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GET /api/seats/{seat_id}
# ---------------------------------------------------------------------------


def test_get_seat_not_found(client: TestClient) -> None:
    resp = client.get("/api/seats/non-existent-id")
    assert resp.status_code == 404
    assert "non-existent-id" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# PATCH /api/seats/{seat_id}/maintenance (admin only)
# ---------------------------------------------------------------------------


def test_set_maintenance_admin_only(cashier_client: TestClient) -> None:
    """Cashier role should be denied when calling set_maintenance."""
    resp = cashier_client.patch("/api/seats/123/maintenance", json={"note": "test"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/seats/{seat_id}/maintenance (admin only)
# ---------------------------------------------------------------------------


def test_clear_maintenance_admin_only(cashier_client: TestClient) -> None:
    """Cashier role should be denied when calling clear_maintenance."""
    resp = cashier_client.delete("/api/seats/123/maintenance")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Auth / role checks
# ---------------------------------------------------------------------------


def test_list_seats_requires_auth() -> None:
    """Accessing /api/seats without a valid token should be rejected."""
    # Ensure no auth override is active
    if get_current_staff in app.dependency_overrides:
        del app.dependency_overrides[get_current_staff]

    with TestClient(app) as c:
        resp = c.get("/api/seats")
    # Expect 401 because no Authorization header
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/seats/{seat_id}/wol (admin only)
# ---------------------------------------------------------------------------


def test_trigger_wol_admin_only(cashier_client: TestClient) -> None:
    """Cashier role should be denied when calling trigger WoL."""
    resp = cashier_client.post("/api/seats/123/wol")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/seats/{seat_id}/wol/override (admin only)
# ---------------------------------------------------------------------------


def test_wol_override_admin_only(cashier_client: TestClient) -> None:
    """Cashier role should be denied when calling WoL override."""
    resp = cashier_client.post("/api/seats/123/wol/override")
    assert resp.status_code == 403
