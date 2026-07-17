"""Tests for Task 1 enum additions (6.5.4)."""

from __future__ import annotations

from backend.models._enums import AuditAction, SeatStatus


def test_seat_status_expired_exists():
    assert SeatStatus.EXPIRED.value == "EXPIRED"


def test_audit_session_extended_exists():
    assert AuditAction.SESSION_EXTENDED.value == "SESSION_EXTENDED"
