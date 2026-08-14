"""Tests for Feature 3.1.3: Package Drawdown."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import EntitlementStatus, MemberPackageEntitlement
from backend.models._enums import PaymentMethod, PricingModel
from backend.repositories import (
    member_repo,
    package_repo,
    seat_repo,
    session_repo,
    zone_repo,
)
from backend.services.billing_service import checkout_session


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB.

    Using a file-based DB instead of in-memory avoids aiosqlite threading issues
    during test cleanup (Windows fatal exception on engine.dispose()).
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


async def _create_active_session(
    db_sess, *, member_id=None, package_entitlement_id=None, duration=30
):
    zone = await zone_repo.create(
        db_sess,
        name="Test",
        rate_per_minute_paise=100,
        rate_per_hour_paise=6000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    seat = await seat_repo.create(db_sess, name="PC-01", zone_id=zone.id)
    sess = await session_repo.create(
        db_sess,
        seat_id=seat.id,
        member_id=member_id,
        started_at=datetime.now(UTC) - timedelta(minutes=duration),
        locked_rate_paise=100,
        locked_pricing_model=PricingModel.PER_MINUTE,
        package_entitlement_id=package_entitlement_id,
    )
    return sess, seat, zone


async def _create_member_with_entitlement(db_sess, *, remaining_minutes):
    member = await member_repo.create(db_sess, name="Alice", phone="555-0001")
    pkg = await package_repo.create(
        db_sess,
        name="Hour",
        type="HOUR_BUNDLE",
        total_minutes=60,
        price_paise=5000,
    )
    ent = MemberPackageEntitlement(
        member_id=member.id,
        package_id=pkg.id,
        remaining_minutes=remaining_minutes,
        status=EntitlementStatus.ACTIVE,
    )
    db_sess.add(ent)
    await db_sess.flush()
    await db_sess.refresh(ent)
    return member, pkg, ent


async def test_drawdown_full_coverage(db):
    member, _, ent = await _create_member_with_entitlement(db, remaining_minutes=60)
    sess, _, _ = await _create_active_session(
        db, member_id=member.id, package_entitlement_id=ent.id, duration=30
    )
    invoice = await checkout_session(db, sess.id, PaymentMethod.CASH)
    assert invoice.time_charge_paise == 0
    assert invoice.package_credit_used_paise == 3000
    await db.refresh(ent)
    assert ent.remaining_minutes == 30


async def test_drawdown_with_overflow(db):
    member, _, ent = await _create_member_with_entitlement(db, remaining_minutes=60)
    sess, _, _ = await _create_active_session(
        db,
        member_id=member.id,
        package_entitlement_id=ent.id,
        duration=90,
    )
    invoice = await checkout_session(db, sess.id, PaymentMethod.CASH)
    assert invoice.time_charge_paise == 3000  # 30 min overflow * 100
    assert invoice.package_credit_used_paise == 6000  # 60 min * 100
    assert invoice.total_paise == 3000
    await db.refresh(ent)
    assert ent.status == EntitlementStatus.EXHAUSTED


async def test_no_package_charges_normally(db):
    sess, _, _ = await _create_active_session(db, duration=30)
    invoice = await checkout_session(db, sess.id, PaymentMethod.CASH)
    assert invoice.time_charge_paise == 3000
    assert invoice.package_credit_used_paise == 0
    assert invoice.total_paise == 3000


async def test_partial_package_exhausted(db):
    member, _, ent = await _create_member_with_entitlement(db, remaining_minutes=30)
    sess, _, _ = await _create_active_session(
        db,
        member_id=member.id,
        package_entitlement_id=ent.id,
        duration=60,
    )
    invoice = await checkout_session(db, sess.id, PaymentMethod.CASH)
    assert invoice.time_charge_paise == 3000  # 30 min overflow
    assert invoice.package_credit_used_paise == 3000  # 30 min used
    assert invoice.total_paise == 3000
    await db.refresh(ent)
    assert ent.remaining_minutes == 0
    assert ent.status == EntitlementStatus.EXHAUSTED


async def test_concurrent_drawdown_no_overspend():
    """D.8: two sessions drawing from the same package concurrently.

    Both checkouts run on separate DB sessions (as in production) via
    asyncio.gather. The entitlement must never be overspent (remaining never
    negative), and the aggregate billing must be deterministic regardless of
    which checkout wins the race: 40-min package covers 40 of the 50 total
    minutes; 10 minutes of overflow billed at the locked per-minute rate.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)

        # Set up: one entitlement (40 min), two seats, two sessions (30 + 20 min)
        async with Session() as setup:
            member, _, ent = await _create_member_with_entitlement(
                setup, remaining_minutes=40
            )
            zone = await zone_repo.create(
                setup,
                name="Test",
                rate_per_minute_paise=100,
                rate_per_hour_paise=6000,
                pricing_model=PricingModel.PER_MINUTE,
            )
            seat_a = await seat_repo.create(setup, name="PC-A", zone_id=zone.id)
            seat_b = await seat_repo.create(setup, name="PC-B", zone_id=zone.id)
            now = datetime.now(UTC)
            sess_a = await session_repo.create(
                setup,
                seat_id=seat_a.id,
                member_id=member.id,
                started_at=now - timedelta(minutes=30),
                locked_rate_paise=100,
                locked_pricing_model=PricingModel.PER_MINUTE,
                package_entitlement_id=ent.id,
            )
            sess_b = await session_repo.create(
                setup,
                seat_id=seat_b.id,
                member_id=member.id,
                started_at=now - timedelta(minutes=20),
                locked_rate_paise=100,
                locked_pricing_model=PricingModel.PER_MINUTE,
                package_entitlement_id=ent.id,
            )
            await setup.commit()
            ent_id = ent.id

        async def _checkout(session_id: str):
            async with Session() as checkout_db:
                invoice = await checkout_session(
                    checkout_db, session_id, PaymentMethod.CASH
                )
                await checkout_db.commit()
                return invoice

        inv_a, inv_b = await asyncio.gather(_checkout(sess_a.id), _checkout(sess_b.id))

        # No overspend: exactly 40 of 40 minutes consumed, never negative
        async with Session() as verify:
            ent = await package_repo.get_entitlement_by_id(verify, ent_id)
            assert ent is not None
            assert ent.remaining_minutes == 0
            assert ent.status == EntitlementStatus.EXHAUSTED

        # Aggregate billing is deterministic: 40 min package credit + 10 min
        # overflow = 1000 paise billed (package credit is informational, not
        # part of total_paise), no matter which checkout won the race
        assert inv_a.package_credit_used_paise + inv_b.package_credit_used_paise == 4000
        assert inv_a.time_charge_paise + inv_b.time_charge_paise == 1000
        assert inv_a.total_paise + inv_b.total_paise == 1000
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)
