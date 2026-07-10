"""Tests for enum definitions."""

from __future__ import annotations


def test_audit_action_has_package_sold():
    from backend.models._enums import AuditAction

    assert hasattr(AuditAction, "PACKAGE_SOLD")
    assert AuditAction.PACKAGE_SOLD.value == "PACKAGE_SOLD"
