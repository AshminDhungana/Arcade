"""AC-10: Shift reconciliation — cash counts match expected values."""

import pytest

from backend.core.feature_flags import _flag_cache
from backend.models import PaymentMethod, ShiftStatus, Staff, StaffRole
from backend.models._enums import InvoicePrintStatus
from backend.repositories import shift_repo
from backend.services import shift_service


async def test_shift_open_creates_record(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Opening a shift creates a shift record with opening float."""
    staff = Staff(
        id="cashier-id",
        name="Cashier",
        pin_hash="argon2id$",
        role=StaffRole.CASHIER,
        is_active=True,
        token_version=0,
    )
    integration_db.add(staff)
    await integration_db.commit()

    shift = await shift_service.open_shift(
        integration_db, staff_id=staff.id, opening_cash_paise=50000
    )
    await integration_db.commit()

    assert shift.id is not None
    assert shift.opened_by_staff_id == staff.id
    assert shift.float_paise == 50000
    assert shift.status == ShiftStatus.OPEN
    assert shift.opened_at is not None
    assert shift.closed_at is None


async def test_shift_close_rejects_when_no_open_shift(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Closing shift fails with 409 when no shift is open."""
    staff = Staff(
        id="cashier-id",
        name="Cashier",
        pin_hash="argon2id$",
        role=StaffRole.CASHIER,
        is_active=True,
        token_version=0,
    )
    integration_db.add(staff)
    await integration_db.commit()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await shift_service.close_shift(
            integration_db, staff_id=staff.id, closing_cash_paise=50000
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "NO_OPEN_SHIFT"


async def test_shift_close_computes_expected_cash(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Shift close computes expected_cash = float + cash_invoices."""
    # Open shift with 500.00 float
    shift = await shift_service.open_shift(
        integration_db, staff_id=admin_staff.id, opening_cash_paise=50000
    )
    await integration_db.commit()

    # Create some invoices with CASH payment
    from backend.models import Invoice

    inv1 = Invoice(
        id="inv-1",
        session_id="sess-1",
        member_id=None,
        shift_id=shift.id,
        time_charge_paise=10000,
        package_credit_used_paise=0,
        pos_total_paise=0,
        discount_paise=0,
        total_paise=10000,
        payment_method=PaymentMethod.CASH,
        print_status=InvoicePrintStatus.PRINTED,
    )
    inv2 = Invoice(
        id="inv-2",
        session_id="sess-2",
        member_id=None,
        shift_id=shift.id,
        time_charge_paise=20000,
        package_credit_used_paise=0,
        pos_total_paise=0,
        discount_paise=0,
        total_paise=20000,
        payment_method=PaymentMethod.CASH,
        print_status=InvoicePrintStatus.PRINTED,
    )
    integration_db.add_all([inv1, inv2])
    await integration_db.commit()

    # Close shift with counted cash = 1200.00 (float 500 + cash sales 300)
    shift = await shift_service.close_shift(
        integration_db, staff_id=admin_staff.id, closing_cash_paise=120000
    )
    await integration_db.commit()

    # Verify expected cash = float_paise + cash_collected_paise = 50000 + 30000 = 80000
    # variance = counted - expected = 120000 - 80000 = 40000 (400.00 over)
    report = await shift_service.get_shift_report(integration_db, shift_id=shift.id)

    assert report.expected_cash_paise == 80000  # 500 + 300
    assert report.cash_collected_paise == 30000
    assert report.variance_paise == 40000  # 1200 - 800


async def test_shift_report_variance_none_when_open(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Shift report shows variance=None while shift is still open."""
    shift = await shift_service.open_shift(
        integration_db, staff_id=admin_staff.id, opening_cash_paise=50000
    )
    await integration_db.commit()

    report = await shift_service.get_shift_report(integration_db, shift_id=shift.id)

    assert report.shift.status == ShiftStatus.OPEN
    assert report.variance_paise is None


async def test_shift_close_unprinted_block_flag(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Shift close blocks when unprinted invoices exist and flag is enabled."""
    from fastapi import HTTPException

    # Enable blocking flag
    _flag_cache["block_shift_close_unprinted"] = True

    # Open shift
    shift = await shift_service.open_shift(
        integration_db, staff_id=admin_staff.id, opening_cash_paise=50000
    )
    await integration_db.commit()

    # Create unprinted invoice
    from backend.models import Invoice

    inv = Invoice(
        id="inv-unprinted",
        session_id="sess-1",
        member_id=None,
        shift_id=shift.id,
        time_charge_paise=10000,
        package_credit_used_paise=0,
        pos_total_paise=0,
        discount_paise=0,
        total_paise=10000,
        payment_method=PaymentMethod.CASH,
        print_status=InvoicePrintStatus.FAILED,
    )
    integration_db.add(inv)
    await integration_db.commit()

    # Attempt to close - should block
    with pytest.raises(HTTPException) as exc_info:
        await shift_service.close_shift(
            integration_db, staff_id=admin_staff.id, closing_cash_paise=60000
        )

    assert exc_info.value.status_code == 409
    assert "UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE" in exc_info.value.detail

    # Shift should still be open
    open_shift = await shift_repo.get_open_shift(integration_db)
    assert open_shift.id == shift.id

    # Disable flag and try again
    _flag_cache["block_shift_close_unprinted"] = False
    shift = await shift_service.close_shift(
        integration_db, staff_id=admin_staff.id, closing_cash_paise=60000
    )

    # Now closes with warning audit
    assert shift.status == ShiftStatus.CLOSED


async def test_shift_close_with_card_payments_ignored_for_cash(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Card payments don't contribute to expected cash."""
    shift = await shift_service.open_shift(
        integration_db, staff_id=admin_staff.id, opening_cash_paise=50000
    )
    await integration_db.commit()

    from backend.models import Invoice

    inv_cash = Invoice(
        id="inv-cash",
        session_id="sess-1",
        member_id=None,
        shift_id=shift.id,
        time_charge_paise=10000,
        total_paise=10000,
        payment_method=PaymentMethod.CASH,
        print_status=InvoicePrintStatus.PRINTED,
    )
    inv_card = Invoice(
        id="inv-card",
        session_id="sess-2",
        member_id=None,
        shift_id=shift.id,
        time_charge_paise=20000,
        total_paise=20000,
        payment_method=PaymentMethod.CARD,
        print_status=InvoicePrintStatus.PRINTED,
    )
    integration_db.add_all([inv_cash, inv_card])
    await integration_db.commit()

    shift = await shift_service.close_shift(
        integration_db, staff_id=admin_staff.id, closing_cash_paise=60000
    )
    await integration_db.commit()

    report = await shift_service.get_shift_report(integration_db, shift_id=shift.id)

    # Expected cash = float + CASH invoices only = 50000 + 10000 = 60000
    # Card payment (20000) is NOT included in expected cash
    assert report.expected_cash_paise == 60000
    assert report.cash_collected_paise == 10000
    assert report.total_revenue_paise == 30000  # Total revenue includes both
    assert report.variance_paise == 0


async def test_shift_close_wallet_payments(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Wallet payments are NOT treated like cash for reconciliation (current implementation)."""
    shift = await shift_service.open_shift(
        integration_db, staff_id=admin_staff.id, opening_cash_paise=50000
    )
    await integration_db.commit()

    from backend.models import Invoice

    inv_wallet = Invoice(
        id="inv-wallet",
        session_id="sess-1",
        member_id=None,
        shift_id=shift.id,
        time_charge_paise=15000,
        total_paise=15000,
        payment_method=PaymentMethod.WALLET,
        print_status=InvoicePrintStatus.PRINTED,
    )
    integration_db.add(inv_wallet)
    await integration_db.commit()

    shift = await shift_service.close_shift(
        integration_db, staff_id=admin_staff.id, closing_cash_paise=50000
    )
    await integration_db.commit()

    report = await shift_service.get_shift_report(integration_db, shift_id=shift.id)

    # WALLET is NOT treated as CASH for reconciliation (only CASH is)
    assert report.expected_cash_paise == 50000  # Only float, wallet not included
    assert report.cash_collected_paise == 0
    assert report.total_revenue_paise == 15000  # Total revenue includes wallet
    assert report.variance_paise == 0  # counted = float = 50000
