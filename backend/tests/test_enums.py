"""Tests for enum definitions."""

from __future__ import annotations


def test_audit_action_has_package_sold():
    from backend.models._enums import AuditAction

    assert hasattr(AuditAction, "PACKAGE_SOLD")
    assert AuditAction.PACKAGE_SOLD.value == "PACKAGE_SOLD"


def test_invoice_print_status_enum_members():
    from backend.models._enums import InvoicePrintStatus

    assert InvoicePrintStatus.PENDING.value == "PENDING"
    assert InvoicePrintStatus.PRINTED.value == "PRINTED"
    assert InvoicePrintStatus.FAILED.value == "FAILED"
    assert InvoicePrintStatus.SKIPPED.value == "SKIPPED"


def test_checkout_forced_unprinted_present():
    from backend.models._enums import AuditAction

    assert AuditAction.CHECKOUT_FORCED_UNPRINTED.value == "CHECKOUT_FORCED_UNPRINTED"
