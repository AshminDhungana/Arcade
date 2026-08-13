"""B.9 — the audit API exposes read-only routes only."""

from __future__ import annotations

from collections.abc import Iterable

from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from backend.main import app


def _iter_routes(routes: Iterable[BaseRoute]) -> Iterable[BaseRoute]:
    """Flatten routes, descending into FastAPI-included sub-routers."""
    for route in routes:
        nested = getattr(route, "original_router", None)
        if nested is not None:
            yield from _iter_routes(nested.routes)
        else:
            yield route


def test_audit_routes_are_read_only() -> None:
    audit_methods: set[tuple[str | None, str]] = {
        (method, route.path)
        for route in _iter_routes(app.routes)
        if isinstance(route, APIRoute)
        and (route.path.startswith("/api/audit") or route.path.startswith("/audit"))
        for method in getattr(route, "methods", set()) or set()
    }
    assert audit_methods, "expected at least one audit route"
    mutating = {
        (m, p) for (m, p) in audit_methods if m in {"PUT", "DELETE", "PATCH", "POST"}
    }
    assert mutating == set(), f"mutating audit routes found: {mutating}"
    assert any(m == "GET" for m, _ in audit_methods)
