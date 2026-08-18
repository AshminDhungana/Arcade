# backend/tests/test_pl_service.py
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.models import Invoice, Member, Staff
from backend.models._enums import ExpenseCategory, MemberTier, PaymentMethod, StaffRole
from backend.repositories import expense_repo
from backend.services import pl_service


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_pl_summary_basic(db: AsyncSession) -> None:
    """Revenue - expenses = net profit."""
    # Seed: 2 invoices (time + POS), 2 expenses
    member = Member(name="Test", phone="+9779800000001", tier=MemberTier.BRONZE.value)
    db.add(member)
    staff = Staff(
        id="staff1",
        name="Admin",
        pin_hash="hash",
        role=StaffRole.ADMIN,
        is_active=True,
        token_version=0,
    )
    db.add(staff)
    await db.flush()

    # Invoice 1: time 3000 + POS 2000 = 5000
    inv1 = Invoice(
        session_id="s1",
        member_id=member.id,
        shift_id=None,
        time_charge_paise=3000,
        package_credit_used_paise=0,
        discount_paise=0,
        pos_total_paise=2000,
        total_paise=5000,
        payment_method=PaymentMethod.CASH,
        created_at=datetime.now(UTC),
    )
    # Invoice 2: time 4000 + POS 1000 = 5000
    inv2 = Invoice(
        session_id="s2",
        member_id=member.id,
        shift_id=None,
        time_charge_paise=4000,
        package_credit_used_paise=0,
        discount_paise=0,
        pos_total_paise=1000,
        total_paise=5000,
        payment_method=PaymentMethod.CARD,
        created_at=datetime.now(UTC),
    )
    db.add_all([inv1, inv2])

    await expense_repo.create(
        db,
        date=date.today().isoformat(),
        category="RENT",
        amount_paise=5000000,
        logged_by_staff_id="staff1",
    )
    await expense_repo.create(
        db,
        date=date.today().isoformat(),
        category="ELECTRICITY",
        amount_paise=150000,
        logged_by_staff_id="staff1",
    )
    await db.commit()

    summary = await pl_service.get_pl_summary(db, date.today(), date.today())

    assert summary.total_revenue_paise == 10000
    assert summary.session_revenue_paise == 7000
    assert summary.pos_revenue_paise == 3000
    assert summary.total_expenses_paise == 5150000
    assert summary.expenses_by_category[ExpenseCategory.RENT] == 5000000
    assert summary.expenses_by_category[ExpenseCategory.ELECTRICITY] == 150000
    assert summary.gross_profit_paise == 10000  # no COGS tracking yet
    assert summary.net_profit_paise == 10000 - 5150000  # negative


async def test_pl_summary_empty(db: AsyncSession) -> None:
    """Empty period returns zeros."""
    summary = await pl_service.get_pl_summary(db, date(2020, 1, 1), date(2020, 1, 31))
    assert summary.total_revenue_paise == 0
    assert summary.total_expenses_paise == 0
    assert summary.gross_profit_paise == 0
    assert summary.net_profit_paise == 0
    assert summary.expenses_by_category == {}
