"""Integration tests for the Inventory API router.

Uses :class:`fastapi.testclient.TestClient` with dependency overrides to
bypass JWT auth in favour of a mock staff object.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_current_staff
from backend.core.feature_flags import _flag_cache
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
        _flag_cache["enable_inventory"] = True  # set after lifespan clears cache
        yield c

    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_inventory", None)


@pytest.fixture
def cashier_client() -> Iterator[TestClient]:
    """Yield a TestClient authenticated as a cashier (not admin)."""
    mock_staff = _make_mock_staff("CASHIER")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        _flag_cache["enable_inventory"] = True  # set after lifespan clears cache
        yield c

    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_inventory", None)


# ---------------------------------------------------------------------------
# POST /api/inventory/restock (admin only)
# ---------------------------------------------------------------------------


def test_restock_missing_item(client: TestClient) -> None:
    """Restocking a non-existent item returns 404."""
    body = {"menu_item_id": "no-such-id", "quantity": 10}
    resp = client.post("/api/inventory/restock", json=body)
    assert resp.status_code == 404


def test_restock_feature_flag_off(client: TestClient) -> None:
    """When enable_inventory is off, POST returns 503."""
    _flag_cache["enable_inventory"] = False
    body = {"menu_item_id": "non-id", "quantity": 10}
    resp = client.post("/api/inventory/restock", json=body)
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/inventory/low-stock (cashier+)
# ---------------------------------------------------------------------------


def test_low_stock_feature_flag_off(client: TestClient) -> None:
    """When enable_inventory is off, GET returns 503."""
    _flag_cache["enable_inventory"] = False
    resp = client.get("/api/inventory/low-stock")
    assert resp.status_code == 503
