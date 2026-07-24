"""AC-03: End-to-end checkout with time charge, package drawdown, POS items, receipt fields all correct."""

from datetime import UTC, datetime, timedelta


async def test_checkout_time_charge_package_pos_receipt(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """End-to-end checkout: time charge, package drawdown, POS items, receipt fields all correct."""
    # Enable feature flags
    from backend.core.feature_flags import _flag_cache
    from backend.models import (
        InvoiceLineItemType,
        MemberTier,
        PackageType,
        PaymentMethod,
        SeatStatus,
    )
    from backend.repositories import inventory_repo, member_repo, package_repo
    from backend.services import (
        billing_service,
        package_service,
        pos_service,
        session_service,
    )

    _flag_cache["enable_packages"] = True
    _flag_cache["enable_pos"] = True
    _flag_cache["enable_inventory"] = True

    # 1. Create member with 2-hour package (120 min)
    member = await member_repo.create(
        integration_db, name="Test Member", phone="9999999999"
    )
    member.tier = MemberTier.BRONZE
    await integration_db.commit()

    package = await package_repo.create(
        integration_db,
        name="2hr Package",
        type=PackageType.HOUR_BUNDLE,
        total_minutes=120,
        price_paise=50000,
        is_active=True,
    )
    await integration_db.commit()

    entitlement = await package_service.PackageService.sell_package(
        integration_db,
        member_id=member.id,
        package_id=package.id,
        payment_method="CASH",
        staff=admin_staff,
    )
    await integration_db.commit()
    print(
        f"Created entitlement: {entitlement.id}, remaining: {entitlement.remaining_minutes}"
    )

    # 2. Start session with member + package
    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session_response = await session_service.start_session(
        integration_db, seeded_seat.id, member.id, admin_staff
    )
    print(
        f"Session created: {session_response.id}, package_entitlement_id: {session_response.package_entitlement_id}"
    )

    # Get the actual ORM object to modify timestamps
    from backend.repositories import session_repo

    session = await session_repo.get_by_id(integration_db, session_response.id)
    session.package_entitlement_id = entitlement.id
    await integration_db.commit()

    # 3. Simulate 150 minutes elapsed (30 min overflow)
    session.started_at = datetime.now(UTC) - timedelta(minutes=150)
    await integration_db.commit()

    # Verify session state before checkout
    refreshed = await package_repo.get_entitlement_by_id(integration_db, entitlement.id)
    print(f"Before checkout - entitlement remaining: {refreshed.remaining_minutes}")

    # 4. Add POS item (create via repo, not service)
    menu_item = await inventory_repo.create(
        integration_db, name="Coffee", price_paise=15000, category="Drinks"
    )
    await pos_service.add_item(
        integration_db,
        session_id=session_response.id,
        menu_item_id=menu_item.id,
        quantity=2,
        staff_id=admin_staff.id,
    )
    await integration_db.commit()

    # 5. Checkout via service layer directly
    invoice = await billing_service.checkout_session(
        integration_db, session.id, PaymentMethod.CASH, admin_staff
    )
    await integration_db.commit()

    print(f"Invoice time_charge: {invoice.time_charge_paise}")
    print(f"Invoice package_credit: {invoice.package_credit_used_paise}")
    print(f"Invoice pos_total: {invoice.pos_total_paise}")

    # 6. Verify all receipt fields
    rate_per_min = seeded_zone.rate_per_minute_paise
    # Package covers 120 min, time charge only for 30 min overflow
    expected_time_charge = 30 * rate_per_min
    expected_package_credit = 120 * rate_per_min
    expected_pos_total = 2 * 15000
    # Total is what customer pays: overflow charge + POS (package already pre-paid)
    expected_total = expected_time_charge + expected_pos_total

    assert (
        invoice.time_charge_paise == expected_time_charge
    ), f"Expected {expected_time_charge}, got {invoice.time_charge_paise}"
    assert invoice.package_credit_used_paise == expected_package_credit
    assert invoice.pos_total_paise == expected_pos_total
    assert invoice.total_paise == expected_total

    # Verify line items
    line_types = {li.type for li in invoice.line_items}
    assert InvoiceLineItemType.TIME_CHARGE in line_types
    assert InvoiceLineItemType.PACKAGE_CREDIT in line_types
    assert InvoiceLineItemType.POS_ITEM in line_types

    assert invoice.payment_method == PaymentMethod.CASH
    # Verify invoice fields (no duration_minutes, seat_name, member_name on Invoice model)
    assert invoice.time_charge_paise == expected_time_charge
    assert invoice.package_credit_used_paise == expected_package_credit
    assert invoice.pos_total_paise == expected_pos_total
    assert invoice.total_paise == expected_total
    assert invoice.session_id == session_response.id
    assert invoice.member_id == member.id
    assert invoice.payment_method == PaymentMethod.CASH

    # Package entitlement exhausted
    refreshed = await package_repo.get_entitlement_by_id(integration_db, entitlement.id)
    assert refreshed.remaining_minutes == 0
    assert refreshed.status.value == "EXHAUSTED"
