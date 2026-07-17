"""Tests that overlay_forced exists on the schema and audit enums."""

from __future__ import annotations

from backend.models._enums import AuditAction
from backend.schemas.seat import SeatResponse


def test_seat_response_includes_overlay_forced() -> None:
    resp = SeatResponse(
        id="s1",
        name="PC-1",
        zone_id="z1",
        status="AVAILABLE",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
    )
    assert resp.overlay_forced is False


def test_audit_action_has_overlay_forced() -> None:
    assert AuditAction.OVERLAY_FORCED_ON.value == "OVERLAY_FORCED_ON"
    assert AuditAction.OVERLAY_FORCED_OFF.value == "OVERLAY_FORCED_OFF"
