# backend/tests/test_expenses_router.py
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.main import app
from backend.models._enums import StaffRole


def _mock_staff(role: StaffRole):
    class _S:
        id = "mock-staff-id"
        name = "Mock"
        is_active = True
        token_version = 0

    s = _S()
    s.role = role
    return s


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


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def cashier_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def test_create_expense_admin(admin_client: AsyncClient):
    resp = await admin_client.post(
        "/api/expenses",
        json={
            "date": "2026-08-18",
            "category": "RENT",
            "amount_paise": 5000000,
            "note": "August rent",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "RENT"
    assert data["amount_paise"] == 5000000
    assert "id" in data


async def test_create_expense_forbidden_cashier(cashier_client: AsyncClient):
    resp = await cashier_client.post(
        "/api/expenses",
        json={"date": "2026-08-18", "category": "RENT", "amount_paise": 5000000},
    )
    assert resp.status_code == 403


async def test_list_expenses(admin_client: AsyncClient, db: AsyncSession):
    # Create via repo directly
    from backend.repositories import expense_repo

    await expense_repo.create(
        db,
        date="2026-08-18",
        category="RENT",
        amount_paise=5000000,
        logged_by_staff_id="mock-staff-id",
    )
    await expense_repo.create(
        db,
        date="2026-08-17",
        category="ELECTRICITY",
        amount_paise=150000,
        logged_by_staff_id="mock-staff-id",
    )
    await db.commit()

    resp = await admin_client.get("/api/expenses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Newest by created_at first (ELECTRICITY created second)
    assert data[0]["category"] == "ELECTRICITY"


async def test_delete_expense(admin_client: AsyncClient, db: AsyncSession):
    from backend.repositories import expense_repo

    exp = await expense_repo.create(
        db,
        date="2026-08-18",
        category="RENT",
        amount_paise=5000000,
        logged_by_staff_id="mock-staff-id",
    )
    await db.commit()

    resp = await admin_client.delete(f"/api/expenses/{exp.id}")
    assert resp.status_code == 204

    # Verify deleted
    resp = await admin_client.get("/api/expenses")
    assert len(resp.json()) == 0


async def test_delete_nonexistent_404(admin_client: AsyncClient):
    resp = await admin_client.delete("/api/expenses/nonexistent")
    assert resp.status_code == 404
