"""HTTP-layer tests for the remote command routes on /api/seats.

Auth is bypassed via dependency_overrides; service functions are mocked so
these tests cover routing, role gating, status codes, and response bodies
(the business logic itself is covered in test_remote_commands.py).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_current_staff
from backend.main import app


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


# --- message (cashier+) ----------------------------------------------------


def test_message_cashier_ok(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "send_message", new=AsyncMock()) as m:
        resp = client.post("/api/seats/seat-1/message", json={"message": "hi"})
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_message_requires_body(client: TestClient) -> None:
    resp = client.post("/api/seats/seat-1/message", json={})
    assert resp.status_code == 422


# --- screenshot (cashier+) -------------------------------------------------


def test_screenshot_returns_jpeg(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(
        rcs, "request_screenshot", new=AsyncMock(return_value=b"\xff\xd8\xff\xff\xd9")
    ):
        resp = client.get("/api/seats/seat-1/screenshot")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/jpeg")
    assert resp.content == b"\xff\xd8\xff\xff\xd9"


# --- restart / shutdown (admin only) ---------------------------------------


def test_restart_admin_ok(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "restart_seat", new=AsyncMock()) as m:
        resp = client.post("/api/seats/seat-1/restart")
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_restart_denied_for_cashier(cashier_client: TestClient) -> None:
    resp = cashier_client.post("/api/seats/seat-1/restart")
    assert resp.status_code == 403


def test_shutdown_admin_ok(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "shutdown_seat", new=AsyncMock()) as m:
        resp = client.post("/api/seats/seat-1/shutdown")
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_shutdown_denied_for_cashier(cashier_client: TestClient) -> None:
    resp = cashier_client.post("/api/seats/seat-1/shutdown")
    assert resp.status_code == 403


# --- offline / not-found passthrough ---------------------------------------


def test_message_503_when_offline(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from fastapi import HTTPException

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "send_message", new=AsyncMock()) as m:
        m.side_effect = HTTPException(status_code=503, detail="offline")
        resp = client.post("/api/seats/seat-1/message", json={"message": "hi"})
    assert resp.status_code == 503


def test_restart_404_unknown_seat(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from fastapi import HTTPException

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "restart_seat", new=AsyncMock()) as m:
        m.side_effect = HTTPException(status_code=404, detail="not found")
        resp = client.post("/api/seats/ghost/restart")
    assert resp.status_code == 404


# --- force_overlay (Task 3) --------------------------------------------------


def test_force_overlay_on_admin_ok(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "force_overlay", new=AsyncMock()) as m:
        resp = client.post("/api/seats/seat-1/overlay", json={"show": True})
    assert resp.status_code == 204
    m.assert_awaited_once()


# --- bulk_force_overlay (Task 4) --------------------------------------------


def test_bulk_overlay_admin_ok(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    summary = {"succeeded": ["seat-1"], "failed": []}
    mock_bulk = AsyncMock(return_value=summary)
    with patch.object(rcs, "bulk_force_overlay", new=mock_bulk) as m:
        resp = client.post("/api/seats/bulk/overlay", json={"show": True})
    assert resp.status_code == 200
    assert resp.json() == {"succeeded": ["seat-1"], "failed": []}
    m.assert_awaited_once()


def test_bulk_overlay_denied_for_cashier(cashier_client: TestClient) -> None:
    resp = cashier_client.post("/api/seats/bulk/overlay", json={"show": True})
    assert resp.status_code == 403


def test_force_overlay_requires_body(client: TestClient) -> None:
    resp = client.post("/api/seats/seat-1/overlay", json={})
    assert resp.status_code == 422


def test_force_overlay_denied_for_cashier(cashier_client: TestClient) -> None:
    resp = cashier_client.post("/api/seats/seat-1/overlay", json={"show": True})
    assert resp.status_code == 403
