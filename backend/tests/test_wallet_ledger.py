"""Tests for wallet transaction ledger (topup writes a row; list returns it)."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.feature_flags import _flag_cache, load_flags
from backend.main import app
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.models.settings import AppSettings
from backend.repositories import member_repo, staff_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            await session.execute(
                insert(AppSettings).values(key="enable_members", value="true")
            )
            await session.commit()
            await load_flags(session)
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def admin_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db,
        name="Admin",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$...",
        role=StaffRole.ADMIN.value,
        is_active=True,
    )


@pytest_asyncio.fixture
async def client(db: AsyncSession, admin_staff: Staff) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_members", None)


@pytest.mark.asyncio
async def test_topup_creates_ledger_row(client: AsyncClient, db: AsyncSession):
    member = await member_repo.create(db, name="Ledger Lee", phone="9800000021")
    await db.commit()
    res = await client.post(
        f"/api/members/{member.id}/topup",
        json={"amount_paise": 500, "payment_method": "CASH"},
    )
    assert res.status_code == 200
    txns = await client.get(f"/api/members/{member.id}/transactions")
    assert txns.status_code == 200
    body = txns.json()
    assert len(body) == 1
    assert body[0]["type"] == "TOPUP"
    assert body[0]["amount_paise"] == 500
    assert body[0]["balance_after_paise"] == 500
    assert body[0]["payment_method"] == "CASH"
    assert body[0]["member_id"] == member.id


@pytest.mark.asyncio
async def test_transactions_404_for_unknown_member(client: AsyncClient):
    res = await client.get("/api/members/does-not-exist/transactions")
    assert res.status_code == 404
