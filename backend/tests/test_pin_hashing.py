"""B.2 — stored PINs are Argon2id hashes, never plaintext."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.core.security import hash_pin
from backend.models._enums import StaffRole
from backend.repositories import staff_repo


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


def test_hash_pin_produces_argon2id() -> None:
    hashed = hash_pin("1234")
    assert hashed.startswith("$argon2id$")
    assert "1234" not in hashed


async def test_created_staff_stores_hash_not_plaintext(db: AsyncSession) -> None:
    created = await staff_repo.create(
        db,
        name="Test Cashier",
        pin_hash=hash_pin("9999"),
        role=StaffRole.CASHIER.value,
        is_active=True,
    )
    assert created.pin_hash.startswith("$argon2id$")
    assert "9999" not in created.pin_hash
