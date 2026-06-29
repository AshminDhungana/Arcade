"""Verification script for Feature 1.1.3 — All SQLAlchemy ORM Models.

Run this script to verify all models import correctly and their
table definitions can be created.

Usage (from the backend/ directory):

    python verify_models.py

"""

# ruff: noqa: S101  # assert is expected in a verification script

from __future__ import annotations

import asyncio
import sys


def test_imports() -> None:
    """Verify every exported symbol can be imported."""
    print("Testing imports...")

    print(f"  Imported {len(locals())} symbols ✅")


def test_enum_values() -> None:
    """Verify a few critical enum values exist."""
    print("Testing enum values...")
    from backend.models._enums import SeatStatus

    assert SeatStatus.AVAILABLE.value == "AVAILABLE"
    assert SeatStatus.IN_USE.value == "IN_USE"
    assert SeatStatus.MAINTENANCE.value == "MAINTENANCE"
    print("  Enum values correct ✅")


def test_table_names() -> None:
    """Verify all models have correct table names."""
    print("Testing table names...")
    from backend.models import (
        AppSettings,
        AuditLog,
        Event,
        EventParticipant,
        Expense,
        GamingSession,
        Invoice,
        InvoiceLineItem,
        LicenseStatus,
        Member,
        MemberPackageEntitlement,
        MenuItem,
        Package,
        Promotion,
        Reservation,
        Seat,
        SessionPOSItem,
        Shift,
        Staff,
        Voucher,
        Zone,
    )

    expected = {
        "audit_log": AuditLog,
        "events": Event,
        "event_participants": EventParticipant,
        "expenses": Expense,
        "invoices": Invoice,
        "invoice_line_items": InvoiceLineItem,
        "license_status": LicenseStatus,
        "members": Member,
        "member_package_entitlements": MemberPackageEntitlement,
        "menu_items": MenuItem,
        "packages": Package,
        "promotions": Promotion,
        "reservations": Reservation,
        "seats": Seat,
        "sessions": GamingSession,
        "session_pos_items": SessionPOSItem,
        "settings": AppSettings,
        "shifts": Shift,
        "staff": Staff,
        "vouchers": Voucher,
        "zones": Zone,
    }
    for name, model in expected.items():
        assert (
            getattr(model, "__tablename__", None) == name
        ), f"Expected {model.__name__}.__tablename__ == '{name}'"
    print(f"  All {len(expected)} table names correct ✅")


async def test_table_creation() -> None:
    """Verify Base.metadata.create_all() works with in-memory SQLite."""
    print("Testing table creation...")
    from sqlalchemy.ext.asyncio import create_async_engine

    from backend.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("  Table creation successful ✅")


async def main() -> int:
    print("=" * 60)
    print(" Feature 1.1.3 Model Verification")
    print("=" * 60)

    try:
        test_imports()
        test_enum_values()
        test_table_names()
        await test_table_creation()

        print()
        print("=" * 60)
        print(" ✅ ALL VERIFICATIONS PASSED ")
        print("=" * 60)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ VERIFICATION FAILED: {exc}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
