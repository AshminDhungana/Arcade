"""AC-11: Package drawdown — entitlements decrement correctly on checkout."""

from datetime import UTC, datetime

from backend.core.feature_flags import _flag_cache
from backend.models import EntitlementStatus, PackageType, PaymentMethod, SeatStatus
from backend.repositories import member_repo, package_repo, session_repo
from backend.services import billing_service, package_service, session_service


async def test_package_drawdown_exhausted_on_checkout(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Package entitlement is fully exhausted after session checkout exceeds package minutes."""
    # Enable feature flags
    _flag_cache["enable_packages"] = True
    _flag_cache["enable_pos"] = True

    # Create member
    from backend.models import MemberTier

    member = await member_repo.create(
        integration_db, name="Package Member", phone="9999999999"
    )
    member.tier = MemberTier.BRONZE
    await integration_db.commit()

    # Create 2-hour package (120 minutes)
    package = await package_repo.create(
        integration_db,
        name="2hr Package",
        type=PackageType.HOUR_BUNDLE,
        total_minutes=120,
        price_paise=50000,
        is_active=True,
    )
    await integration_db.commit()

    # Sell package to member
    entitlement = await package_service.PackageService.sell_package(
        integration_db,
        member_id=member.id,
        package_id=package.id,
        payment_method="CASH",
        staff=admin_staff,
    )
    await integration_db.commit()
    assert entitlement.remaining_minutes == 120

    # Start session with package
    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session = await session_service.start_session(
        integration_db, seeded_seat.id, member.id, admin_staff
    )
    await integration_db.commit()

    # Associate entitlement with session
    session_obj = await session_repo.get_by_id(integration_db, session.id)
    session_obj.package_entitlement_id = entitlement.id
    await integration_db.commit()

    # Simulate 150 minutes elapsed (30 min overflow)
    session_obj.started_at = datetime.now(UTC) - __import__("datetime").timedelta(
        minutes=150
    )
    await integration_db.commit()

    # Checkout
    invoice = await billing_service.checkout_session(
        integration_db, session_obj.id, PaymentMethod.CASH, admin_staff
    )
    await integration_db.commit()

    # Verify entitlement exhausted
    refreshed = await package_repo.get_entitlement_by_id(integration_db, entitlement.id)
    assert refreshed.remaining_minutes == 0
    assert refreshed.status == EntitlementStatus.EXHAUSTED

    # Verify package credit applied = 120 * per_minute_rate
    per_min_rate = seeded_zone.rate_per_minute_paise
    expected_package_credit = 120 * per_min_rate
    assert invoice.package_credit_used_paise == expected_package_credit


async def test_package_drawdown_partial_usage(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Package entitlement partially used when session is shorter than package."""
    _flag_cache["enable_packages"] = True

    member = await member_repo.create(
        integration_db, name="Package Member 2", phone="8888888888"
    )
    await integration_db.commit()

    package = await package_repo.create(
        integration_db,
        name="1hr Package",
        type=PackageType.HOUR_BUNDLE,
        total_minutes=60,
        price_paise=25000,
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

    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session = await session_service.start_session(
        integration_db, seeded_seat.id, member.id, admin_staff
    )
    await integration_db.commit()

    session_obj = await session_repo.get_by_id(integration_db, session.id)
    session_obj.package_entitlement_id = entitlement.id
    # Simulate 30 minutes elapsed
    session_obj.started_at = datetime.now(UTC) - __import__("datetime").timedelta(
        minutes=30
    )
    await integration_db.commit()

    invoice = await billing_service.checkout_session(
        integration_db, session_obj.id, PaymentMethod.CASH, admin_staff
    )
    await integration_db.commit()

    # 30 minutes used, 30 minutes remaining
    refreshed = await package_repo.get_entitlement_by_id(integration_db, entitlement.id)
    assert refreshed.remaining_minutes == 30
    assert refreshed.status == EntitlementStatus.ACTIVE
    expected_credit = 30 * seeded_zone.rate_per_minute_paise
    assert invoice.package_credit_used_paise == expected_credit


async def test_package_drawdown_fifo_multiple_packages(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Multiple packages consumed - only the session's entitlement is drawn down (current behavior)."""
    _flag_cache["enable_packages"] = True

    member = await member_repo.create(
        integration_db, name="Multi Package Member", phone="7777777777"
    )
    await integration_db.commit()

    # Create two packages
    pkg1 = await package_repo.create(
        integration_db,
        name="Pkg 1",
        type=PackageType.HOUR_BUNDLE,
        total_minutes=30,
        price_paise=10000,
        is_active=True,
    )
    pkg2 = await package_repo.create(
        integration_db,
        name="Pkg 2",
        type=PackageType.HOUR_BUNDLE,
        total_minutes=30,
        price_paise=10000,
        is_active=True,
    )
    await integration_db.commit()

    # Sell both
    ent1 = await package_service.PackageService.sell_package(
        integration_db,
        member_id=member.id,
        package_id=pkg1.id,
        payment_method="CASH",
        staff=admin_staff,
    )
    ent2 = await package_service.PackageService.sell_package(
        integration_db,
        member_id=member.id,
        package_id=pkg2.id,
        payment_method="CASH",
        staff=admin_staff,
    )
    await integration_db.commit()

    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session = await session_service.start_session(
        integration_db, seeded_seat.id, member.id, admin_staff
    )
    await integration_db.commit()

    session_obj = await session_repo.get_by_id(integration_db, session.id)
    # Session gets the first (FIFO) entitlement
    session_obj.package_entitlement_id = ent1.id
    # 45 minutes will exhaust first package (30 min) but second package is NOT auto-consumed
    session_obj.started_at = datetime.now(UTC) - __import__("datetime").timedelta(
        minutes=45
    )
    await integration_db.commit()

    invoice = await billing_service.checkout_session(
        integration_db, session_obj.id, PaymentMethod.CASH, admin_staff
    )
    await integration_db.commit()

    # First package partially exhausted (used 30 of 45 minutes), second package untouched (only session's entitlement is used)
    refreshed1 = await package_repo.get_entitlement_by_id(integration_db, ent1.id)
    refreshed2 = await package_repo.get_entitlement_by_id(integration_db, ent2.id)
    # 45 min session, first package has 30 min -> 30 min used, 0 remaining (exhausted)
    assert refreshed1.remaining_minutes == 0
    assert refreshed1.status == EntitlementStatus.EXHAUSTED
    # Second package is NOT touched because it's not attached to the session
    assert refreshed2.remaining_minutes == 30
    # Package credit applied = 30 min * rate (only first package's minutes)
    assert invoice.package_credit_used_paise == 30 * seeded_zone.rate_per_minute_paise


async def test_package_drawdown_timeout_expired(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Package expires after valid_days."""
    _flag_cache["enable_packages"] = True

    member = await member_repo.create(
        integration_db, name="Expired Member", phone="6666666666"
    )
    await integration_db.commit()

    # Package valid for 1 day
    package = await package_repo.create(
        integration_db,
        name="Expires Tomorrow",
        type=PackageType.HOUR_BUNDLE,
        total_minutes=60,
        price_paise=20000,
        is_active=True,
        valid_days=1,
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

    # Manually set expiry to past
    entitlement.expires_at = datetime.now(UTC) - __import__("datetime").timedelta(
        days=1
    )
    await integration_db.commit()

    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session = await session_service.start_session(
        integration_db, seeded_seat.id, member.id, admin_staff
    )
    await integration_db.commit()

    session_obj = await session_repo.get_by_id(integration_db, session.id)
    session_obj.package_entitlement_id = entitlement.id
    await integration_db.commit()

    # Active entitlement check should return None (expired)
    active = await package_service.PackageService.get_active_entitlement(
        integration_db, member.id
    )
    assert active is None


async def test_package_drawdown_no_package_on_walkin(
    integration_client, integration_db, seeded_zone, seeded_seat, admin_staff
):
    """Walk-in session without package gets no package credit."""
    _flag_cache["enable_packages"] = True

    seeded_seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()

    session = await session_service.start_session(
        integration_db, seeded_seat.id, None, admin_staff
    )
    await integration_db.commit()

    session_obj = await session_repo.get_by_id(integration_db, session.id)
    session_obj.started_at = datetime.now(UTC) - __import__("datetime").timedelta(
        minutes=30
    )
    await integration_db.commit()

    invoice = await billing_service.checkout_session(
        integration_db, session_obj.id, PaymentMethod.CASH, admin_staff
    )
    await integration_db.commit()

    assert invoice.package_credit_used_paise == 0
    # Time charge for full 30 minutes
    expected = 30 * seeded_zone.rate_per_minute_paise
    assert invoice.time_charge_paise == expected
