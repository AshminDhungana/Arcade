# backend/tests/test_reports_router.py
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.main import app
from backend.models import Invoice, Member, Staff
from backend.models._enums import MemberTier, PaymentMethod, StaffRole
from backend.repositories import expense_repo


class _MockStaff:
    id = "mock-staff-id"
    name = "Mock"
    is_active = True
    token_version = 0
    role: StaffRole


def _mock_staff(role: StaffRole) -> _MockStaff:
    s = _MockStaff()
    s.role = role
    return s


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
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


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def _seed_pl_data(db: AsyncSession) -> None:
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


async def test_pl_summary_endpoint(admin_client: AsyncClient, db: AsyncSession) -> None:
    await _seed_pl_data(db)

    resp = await admin_client.get("/api/reports/pl/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_revenue_paise"] == 10000
    assert data["total_expenses_paise"] == 5150000
    assert data["net_profit_paise"] == 10000 - 5150000
    assert "RENT" in data["expenses_by_category"]
    assert data["expenses_by_category"]["RENT"] == 5000000


async def test_pl_summary_with_custom_range(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    await _seed_pl_data(db)

    resp = await admin_client.get(
        "/api/reports/pl/summary?start=2026-08-01&end=2026-08-31"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_start"] == "2026-08-01"
    assert data["period_end"] == "2026-08-31"


async def test_pl_monthly_endpoint(admin_client: AsyncClient, db: AsyncSession) -> None:
    await _seed_pl_data(db)

    resp = await admin_client.get(
        f"/api/reports/pl/monthly/{date.today().year}/{date.today().month}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_revenue_paise"] == 10000


async def test_pl_forbidden_cashier(
    admin_client: AsyncClient, db: AsyncSession
) -> None:
    # Need a cashier client
    from backend.api.deps import get_current_staff
    from backend.models._enums import StaffRole

    class _Cashier:
        id = "cashier-id"
        name = "Cashier"
        is_active = True
        token_version = 0
        role = StaffRole.CASHIER

    app.dependency_overrides[get_current_staff] = lambda: _Cashier()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/reports/pl/summary")
        assert resp.status_code == 403
    app.dependency_overrides.pop(get_current_staff, None)
