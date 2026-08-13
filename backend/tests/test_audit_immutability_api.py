"""B.9 — the audit API exposes read-only routes only."""

from __future__ import annotations

from backend.main import app


def test_audit_routes_are_read_only() -> None:
    audit_methods = {
        (method, route.path)
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/audit")
        for method in getattr(route, "methods", set()) or set()
    }
    assert audit_methods, "expected at least one audit route"
    mutating = {
        (m, p) for (m, p) in audit_methods if m in {"PUT", "DELETE", "PATCH", "POST"}
    }
    assert mutating == set(), f"mutating audit routes found: {mutating}"
    assert any(m == "GET" for m, _ in audit_methods)
