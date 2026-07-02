"""Integration tests for the Session API router.

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
# GET /api/sessions/active
# ---------------------------------------------------------------------------


def test_list_active_sessions_empty(client: TestClient) -> None:
    resp = client.get("/api/sessions/active")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_active_sessions_returns_list(client: TestClient) -> None:
    resp = client.get("/api/sessions/active")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}
# ---------------------------------------------------------------------------


def test_get_session_not_found(client: TestClient) -> None:
    resp = client.get("/api/sessions/non-existent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/sessions
# ---------------------------------------------------------------------------


def test_create_session_missing_seat(client: TestClient) -> None:
    resp = client.post("/api/sessions", json={"seat_id": "non-existent-id"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/sessions/{session_id}/pause
# ---------------------------------------------------------------------------


def test_pause_session_not_found(client: TestClient) -> None:
    resp = client.patch("/api/sessions/non-existent-id/pause")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/sessions/{session_id}/resume
# ---------------------------------------------------------------------------


def test_resume_session_not_found(client: TestClient) -> None:
    resp = client.patch("/api/sessions/non-existent-id/resume")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth checks
# ---------------------------------------------------------------------------


def test_list_sessions_requires_auth() -> None:
    """Accessing /api/sessions without a valid token should be rejected."""
    # Ensure no auth override is active
    if get_current_staff in app.dependency_overrides:
        del app.dependency_overrides[get_current_staff]

    with TestClient(app) as c:
        resp = c.get("/api/sessions/active")
    # Expect 401 because no Authorization header
    assert resp.status_code == 401
