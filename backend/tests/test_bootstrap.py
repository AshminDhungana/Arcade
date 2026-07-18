"""Unit tests for ensure_default_staff (idempotent default-account seed)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import Settings
from backend.core.database import Base
from backend.core.security import hash_pin, verify_pin
from backend.models._enums import StaffRole
from backend.repositories import staff_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    import tempfile
    from pathlib import Path

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


def _settings() -> Settings:
    return Settings(
        admin_staff_id="admin",
        admin_pin_hash=hash_pin("admin"),
        cashier_staff_id="cashier",
        cashier_pin_hash=hash_pin("cashier"),
    )


async def test_seeds_admin_and_cashier_with_explicit_ids(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    await ensure_default_staff(db, settings=_settings())
    await db.commit()

    admin = await staff_repo.get_by_id(db, "admin")
    cashier = await staff_repo.get_by_id(db, "cashier")
    assert admin is not None
    assert cashier is not None
    assert admin.role == StaffRole.ADMIN
    assert cashier.role == StaffRole.CASHIER
    assert admin.is_active and cashier.is_active
    assert verify_pin("admin", admin.pin_hash)
    assert verify_pin("cashier", cashier.pin_hash)


async def test_is_idempotent_on_second_call(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    await ensure_default_staff(db, settings=_settings())
    await db.commit()
    # First call creates rows; grab the admin id.
    admin_before = await staff_repo.get_by_id(db, "admin")
    # Second call must NOT create duplicates or error.
    await ensure_default_staff(db, settings=_settings())

    all_staff = await staff_repo.list(db)
    assert len(all_staff) == 2
    admin_after = await staff_repo.get_by_id(db, "admin")
    # Same row, not a new one (id is the fixed "admin").
    assert admin_after.id == admin_before.id == "admin"


async def test_does_not_seed_when_table_non_empty(db: AsyncSession) -> None:
    from backend.core.bootstrap import ensure_default_staff

    # Pre-existing staff (e.g. dev seed or a previously
    # deleted/recreated admin).
    await staff_repo.create(
        db, name="Existing", role="ADMIN", pin_hash=hash_pin("0000")
    )
    await db.commit()

    await ensure_default_staff(db, settings=_settings())

    all_staff = await staff_repo.list(db)
    # Only the pre-existing row; default "admin" is NOT force-created.
    assert len(all_staff) == 1
    assert await staff_repo.get_by_id(db, "admin") is None
