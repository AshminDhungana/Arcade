"""HTTP-layer tests for the Tuya console power routes on /api/seats.

Auth is bypassed via dependency_overrides; the service functions are mocked so
these tests cover routing, feature-flag gating (503), role gating (403), and
status codes. Business logic lives in test_tuya_service.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_current_staff
from backend.main import app
from backend.services import tuya_service


def _mock_staff(role: str = "ADMIN"):
    from backend.models._enums import StaffRole

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock"
        is_active = True
        token_version = 0

    obj = _MockStaff()
    obj.role = StaffRole(role)
    return obj


@pytest.fixture
def client() -> Iterator[TestClient]:
    mock_staff = _mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_staff, None)


@pytest.fixture
def cashier_client() -> Iterator[TestClient]:
    mock_staff = _mock_staff("CASHIER")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_staff, None)


def test_power_on_503_when_flag_off(client: TestClient, monkeypatch) -> None:
    """Without enable_tuya, the route is gated to 503."""
    monkeypatch.setattr("backend.core.feature_flags.get_flag", lambda n: False)
    resp = client.post("/api/seats/seat-1/power-on")
    assert resp.status_code == 503


def test_power_off_503_when_flag_off(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("backend.core.feature_flags.get_flag", lambda n: False)
    resp = client.post("/api/seats/seat-1/power-off")
    assert resp.status_code == 503


def test_power_on_admin_ok(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("backend.core.feature_flags.get_flag", lambda n: True)
    with patch.object(tuya_service, "power_on", new=AsyncMock()) as m:
        resp = client.post("/api/seats/seat-1/power-on")
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_power_off_admin_ok(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("backend.core.feature_flags.get_flag", lambda n: True)
    with patch.object(tuya_service, "power_off", new=AsyncMock()) as m:
        resp = client.post("/api/seats/seat-1/power-off")
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_power_on_denied_for_cashier(cashier_client, monkeypatch) -> None:
    """Power control is admin-only."""
    monkeypatch.setattr("backend.core.feature_flags.get_flag", lambda n: True)
    with patch.object(tuya_service, "power_on", new=AsyncMock()):
        resp = cashier_client.post("/api/seats/seat-1/power-on")
    assert resp.status_code == 403
