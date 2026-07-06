"""Tests for Feature 3.1.3: Package Drawdown."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

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
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


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
