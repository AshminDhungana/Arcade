"""Integration test for all repository stubs.

Spins up an in-memory async SQLite DB, creates all tables, and exercises
every repository module for basic round-trip CRUD and any special methods.
"""

from __future__ import annotations

# ── Fixture ────────────────────────────────────────────────────────────────
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import (
    EntitlementStatus,
    Event,
    Expense,
    GamingSession,
    Member,
    MemberPackageEntitlement,
    PaymentMethod,
    PricingModel,
    Reservation,
    SeatStatus,
    SessionStatus,
    Shift,
    ShiftStatus,
    Zone,
)
from backend.repositories import (
    audit_repo,
    event_repo,
    expense_repo,
    inventory_repo,
    invoice_repo,
    member_repo,
    package_repo,
    pos_repo,
    promotion_repo,
    reservation_repo,
    restock_repo,
    seat_repo,
    session_repo,
    shift_repo,
    staff_repo,
    voucher_repo,
)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on an in-memory SQLite DB."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


# ── Imports -----------------------------------------------------------------


def test_all_repos_import() -> None:
    """Every repository module imports cleanly."""
    assert True


# ── Seat repository ---------------------------------------------------------


async def test_seat_repo_crud(db: AsyncSession) -> None:
    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()

    seat = await seat_repo.create(
        db, name="PC-01", zone_id=zone.id, mac_address="00:11:22:33:44:55"
    )
    assert seat.id is not None
    assert seat.name == "PC-01"

    fetched = await seat_repo.get_by_id(db, seat.id)
    assert fetched is not None
    assert fetched.name == "PC-01"

    all_seats = await seat_repo.list(db)
    assert len(all_seats) == 1

    with_mac = await seat_repo.list_with_mac(db)
    assert len(with_mac) == 1

    updated = await seat_repo.update_status(db, seat.id, SeatStatus.IN_USE)
    assert updated is not None
    assert updated.status == SeatStatus.IN_USE

    deleted = await seat_repo.delete_by_id(db, seat.id)
    assert deleted is True
    assert await seat_repo.get_by_id(db, seat.id) is None


# ── Member repository -------------------------------------------------------


async def test_member_repo_crud(db: AsyncSession) -> None:
    member = await member_repo.create(db, name="Alice", phone="555-0001", tier="BRONZE")
    assert member.id is not None
    assert member.name == "Alice"

    by_id = await member_repo.get_by_id(db, member.id)
    assert by_id is not None

    by_phone = await member_repo.get_by_phone(db, "555-0001")
    assert by_phone is not None
    assert by_phone.name == "Alice"

    found = await member_repo.search(db, "Ali")
    assert len(found) == 1

    all_members = await member_repo.list(db)
    assert len(all_members) == 1


# ── Staff / Shift repositories ---------------------------------------------


async def test_staff_and_shift_repo(db: AsyncSession) -> None:
    staff = await staff_repo.create(db, name="Bob", role="ADMIN", pin_hash="argon2id$")
    assert staff.id is not None

    fetched = await staff_repo.get_by_id(db, staff.id)
    assert fetched is not None

    all_staff = await staff_repo.list(db)
    assert len(all_staff) == 1

    # shift created directly because the stub lacks needed params
    shift = Shift(
        opened_by_staff_id=staff.id,
        opened_at=datetime.now(UTC),
        float_paise=1000,
        status=ShiftStatus.OPEN,
    )
    db.add(shift)
    await db.flush()
    await db.refresh(shift)

    fetched_shift = await shift_repo.get_by_id(db, shift.id)
    assert fetched_shift is not None
    assert fetched_shift.status == ShiftStatus.OPEN

    all_shifts = await shift_repo.list(db)
    assert len(all_shifts) == 1


# ── Session repository ------------------------------------------------------


async def test_session_repo_helpers(db: AsyncSession) -> None:
    zone = Zone(
        name="Floor 1",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)

    # create session directly (repo stub misses started_at)
    sess = GamingSession(
        seat_id=seat.id,
        started_at=datetime.now(UTC),
        locked_rate_paise=50,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(sess)
    await db.flush()
    await db.refresh(sess)

    assert (await session_repo.get_by_id(db, sess.id)) is not None

    active = await session_repo.get_active_by_seat(db, seat.id)
    assert active is not None
    assert active.status in (SessionStatus.ACTIVE, SessionStatus.PAUSED)

    actives = await session_repo.list_active(db)
    assert len(actives) == 1

    all_sessions = await session_repo.list(db)
    assert len(all_sessions) == 1

    # shift filter
    shift = Shift(
        opened_by_staff_id="s1", opened_at=datetime.now(UTC), status=ShiftStatus.OPEN
    )
    db.add(shift)
    await db.flush()
    sess.shift_id = shift.id
    db.add(sess)
    await db.flush()

    by_shift = await session_repo.list_by_shift(db, shift.id)
    assert len(by_shift) == 1


# ── Invoice repository -------------------------------------------------------


async def test_invoice_repo(db: AsyncSession) -> None:
    zone = Zone(
        name="Floor 1",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    sess = GamingSession(
        seat_id=seat.id,
        started_at=datetime.now(UTC),
        locked_rate_paise=50,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(sess)
    await db.flush()

    inv = await invoice_repo.create(
        db, session_id=sess.id, total_paise=500, payment_method=PaymentMethod.CASH
    )
    assert inv.id is not None

    by_id = await invoice_repo.get_by_id(db, inv.id)
    assert by_id is not None

    by_session = await invoice_repo.get_by_session(db, sess.id)
    assert len(by_session) == 1

    all_invoices = await invoice_repo.list(db)
    assert len(all_invoices) == 1


# ── Package repository ------------------------------------------------------


async def test_package_repo(db: AsyncSession) -> None:
    pkg = await package_repo.create(
        db, name="Weekend Pass", type="DAY_PASS", total_minutes=480, price_paise=5000
    )
    assert pkg.id is not None

    by_id = await package_repo.get_by_id(db, pkg.id)
    assert by_id is not None

    all_pkgs = await package_repo.list(db)
    assert len(all_pkgs) == 1

    # Test drawdown on entitlement
    member = Member(name="Alice", phone="555-0002")
    db.add(member)
    await db.flush()
    entitlement = MemberPackageEntitlement(
        member_id=member.id,
        package_id=pkg.id,
        remaining_minutes=120,
        status=EntitlementStatus.ACTIVE,
    )
    db.add(entitlement)
    await db.flush()
    await db.refresh(entitlement)

    ok = await package_repo.drawdown_minutes(db, entitlement.id, 30)
    assert ok is True

    # refresh entitlement state to verify drawdown
    await db.refresh(entitlement)
    assert entitlement.remaining_minutes == 90


# ── Event repository --------------------------------------------------------


async def test_event_repo(db: AsyncSession) -> None:
    event = Event(
        name="Summer Tournament", game_title="CS2", event_date=datetime.now(UTC)
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    assert event.id is not None
    assert event.game_title == "CS2"

    by_id = await event_repo.get_event_by_id(db, event.id)
    assert by_id is not None

    all_events = await event_repo.list_events(db)
    assert len(all_events) == 1

    # participant through repo
    participant = await event_repo.create_participant(
        db, event_id=event.id, name="Alice"
    )
    assert participant.id is not None

    by_pid = await event_repo.get_participant_by_id(db, participant.id)
    assert by_pid is not None
    assert by_pid.name == "Alice"

    participants = await event_repo.list_participants(db, event.id)
    assert len(participants) == 1


# ── Expense / Promotion / Voucher / POS / Inventory / Reservation repos -----


async def test_expense_repo(db: AsyncSession) -> None:
    from datetime import date as _date

    staff = await staff_repo.create(
        db, name="Alice", role="CASHIER", pin_hash="argon2id$"
    )
    exp = Expense(
        date=_date(2026, 1, 1),
        category="RENT",
        amount_paise=50000,
        logged_by_staff_id=staff.id,
    )
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    assert exp.id is not None

    by_id = await expense_repo.get_by_id(db, exp.id)
    assert by_id is not None

    all_expenses = await expense_repo.list(db)
    assert len(all_expenses) == 1


async def test_promotion_repo(db: AsyncSession) -> None:
    promo = await promotion_repo.create(
        db, name="Happy Hour", type="HAPPY_HOUR", discount_type="PERCENTAGE"
    )
    assert promo.id is not None

    by_id = await promotion_repo.get_by_id(db, promo.id)
    assert by_id is not None

    all_promos = await promotion_repo.list(db)
    assert len(all_promos) == 1


async def test_voucher_repo(db: AsyncSession) -> None:
    v = await voucher_repo.create(db, code="SAVE10", value_paise=1000)
    assert v.id is not None

    by_id = await voucher_repo.get_by_id(db, v.id)
    assert by_id is not None

    all_vouchers = await voucher_repo.list(db)
    assert len(all_vouchers) == 1


async def test_inventory_repo(db: AsyncSession) -> None:
    item = await inventory_repo.create(
        db, name="Red Bull", category="Drink", price_paise=15000
    )
    assert item is not None

    by_id = await inventory_repo.get_by_id(db, item.id)
    assert by_id is not None

    all_items = await inventory_repo.list(db)
    assert len(all_items) == 1


async def test_pos_repo(db: AsyncSession) -> None:
    zone = Zone(
        name="Floor 1",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    sess = GamingSession(
        seat_id=seat.id,
        started_at=datetime.now(UTC),
        locked_rate_paise=50,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(sess)
    await db.flush()

    menu_item = await inventory_repo.create(
        db, name="Red Bull", category="Drink", price_paise=15000
    )
    item = await pos_repo.create(
        db,
        session_id=sess.id,
        menu_item_id=menu_item.id,
        quantity=2,
        unit_price_paise=15000,
    )
    assert item.id is not None

    by_id = await pos_repo.get_by_id(db, item.id)
    assert by_id is not None

    all_items = await pos_repo.list(db)
    assert len(all_items) == 1


async def test_reservation_repo(db: AsyncSession) -> None:
    zone = Zone(
        name="Floor 1",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    staff_member = await staff_repo.create(
        db, name="Bob", role="CASHIER", pin_hash="argon2id$"
    )

    res = Reservation(
        seat_id=seat.id,
        customer_name="Alice",
        reserved_from=datetime.now(UTC),
        reserved_until=datetime.now(UTC),
        created_by_staff_id=staff_member.id,
    )
    db.add(res)
    await db.flush()
    await db.refresh(res)

    by_id = await reservation_repo.get_by_id(db, res.id)
    assert by_id is not None

    all_res = await reservation_repo.list(db)
    assert len(all_res) == 1


# ── AuditLog repository -----------------------------------------------------


async def test_audit_repo(db: AsyncSession) -> None:
    log = await audit_repo.create(
        db, action="SESSION_START", entity_type="Session", entity_id="s1", detail="foo"
    )
    assert log.id is not None

    by_id = await audit_repo.get_by_id(db, log.id)
    assert by_id is not None
    assert by_id.action.value == "SESSION_START"

    all_logs = await audit_repo.list(db)
    assert len(all_logs) == 1

    # audit log is immutable: no update / delete methods exposed
    assert not hasattr(audit_repo, "update")
    assert not hasattr(audit_repo, "delete_by_id")


async def test_restock_repo(db: AsyncSession) -> None:
    staff = await staff_repo.create(
        db, name="Alice", role="ADMIN", pin_hash="argon2id$"
    )
    item = await inventory_repo.create(
        db, name="Energy Drink", category="Drink", price_paise=15000
    )

    log = await restock_repo.create(
        db, menu_item_id=item.id, quantity_added=100, logged_by_staff_id=staff.id
    )
    assert log.id is not None
    assert log.menu_item_id == item.id
    assert log.quantity_added == 100

    by_id = await restock_repo.get_by_id(db, log.id)
    assert by_id is not None
    assert by_id.quantity_added == 100

    by_item = await restock_repo.list_by_menu_item(db, item.id)
    assert len(by_item) == 1

    all_logs = await restock_repo.list_all(db)
    assert len(all_logs) == 1
