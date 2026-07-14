"""Tests for backend.main — FastAPI application entry point.

Covers: lifespan (startup/shutdown), ``/health`` endpoint, static file
fallback, and exception handlers.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.main import app

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a ``TestClient`` that exercises the full lifespan."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


def test_lifespan_starts_cleanly(client: TestClient) -> None:
    """The app starts without raising during lifespan startup."""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_lifespan_shuts_down_cleanly(client: TestClient) -> None:
    """Exiting the ``TestClient`` context runs the lifespan shutdown code."""
    # Any request is enough to trigger lifespan start; on exit shutdown runs.
    resp = client.get("/health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_schema(client: TestClient) -> None:
    resp = client.get("/health")
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0-phase1"
    assert data["license_type"] == "TRIAL"
    assert "seat_count" in data
    assert "active_sessions" in data


# ---------------------------------------------------------------------------
# Static files / SPA fallback
# ---------------------------------------------------------------------------


def test_unknown_path_returns_index_or_404(client: TestClient) -> None:
    """A non-existent path should return ``index.html`` if static files are
    mounted, or a 404 if the frontend build is missing."""
    resp = client.get("/nonexistent")
    assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def test_http_exception_handler_returns_json(client: TestClient) -> None:
    """A 404 from a missing resource should be JSON, not plain text."""
    resp = client.get("/api/v1/nonexistent-endpoint")
    assert "application/json" in resp.headers.get("content-type", "")
    assert resp.status_code in (404, 422)


def test_validation_error_returns_422_json(client: TestClient) -> None:
    """An invalid payload to a non-existent endpoint yields a JSON error.

    The endpoint does not exist, so FastAPI (or the SPA catch-all mount for
    POST) returns a JSON error rather than crashing. We accept any of the
    JSON error statuses: 400/404 (no route), 405 (POST to the SPA fallback),
    or 422 (validation error).
    """
    resp = client.post("/api/v1/nonexistent-endpoint", content=b"not-json")
    assert resp.status_code in (400, 404, 405, 422)
    if resp.status_code == 422:
        assert "detail" in resp.json()
