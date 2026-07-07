"""Integration tests for the POS API router.

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
    mock_staff = _make_mock_staff("CASHIER")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        _flag_cache["enable_pos"] = True  # set after lifespan clears cache
        yield c

    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_pos", None)


@pytest.fixture
def admin_client() -> Iterator[TestClient]:
    """Yield a TestClient authenticated as admin (for delete)."""
    mock_staff = _make_mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        _flag_cache["enable_pos"] = True  # set after lifespan clears cache
        yield c

    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_pos", None)


# ---------------------------------------------------------------------------
# POST /api/pos/items
# ---------------------------------------------------------------------------


def test_add_pos_item_missing_session(client: TestClient) -> None:
    """Adding to a non-existent session returns 404."""
    body = {"session_id": "no-such-id", "menu_item_id": "non-id", "quantity": 1}
    resp = client.post("/api/pos/items", json=body)
    assert resp.status_code == 404


def test_add_pos_item_feature_flag_off_admin(admin_client: TestClient) -> None:
    """When enable_pos is off, POST returns 503."""
    _flag_cache["enable_pos"] = False
    body = {"session_id": "no-such-id", "menu_item_id": "non-id", "quantity": 1}
    resp = admin_client.post("/api/pos/items", json=body)
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/pos/items/{session_id}
# ---------------------------------------------------------------------------


def test_list_session_items_feature_flag_off(client: TestClient) -> None:
    """When enable_pos is off, GET returns 503."""
    _flag_cache["enable_pos"] = False
    resp = client.get("/api/pos/items/non-id")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# DELETE /api/pos/items/{id}
# ---------------------------------------------------------------------------


def test_remove_pos_item_not_found(admin_client: TestClient) -> None:
    """Removing a non-existent item returns 404 or 200 with deleted=False."""
    resp = admin_client.delete("/api/pos/items/non-id?session_id=test")
    assert resp.status_code == 200
    assert resp.json().get("deleted") is False
