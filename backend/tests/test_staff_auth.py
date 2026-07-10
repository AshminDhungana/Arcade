"""Integration tests for staff JWT invalidation via token_version.

Covers the security-critical property from the spec: bumping
``token_version`` on PIN change / deactivation rejects previously valid
JWTs on the very next request (via ``get_current_staff``).
"""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.security import (
    create_access_token,
    get_current_staff,
    hash_pin,
)
from backend.models._enums import StaffRole
from backend.models.staff import Staff
from backend.repositories import staff_repo
from backend.services.staff_service import StaffService


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
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


async def _token_for(staff: Staff) -> str:
    return create_access_token(staff.id, str(staff.role), staff.token_version)


class TestTokenInvalidation:
    async def test_stale_token_rejected_after_pin_change(
        self, db: AsyncSession
    ) -> None:
        staff = await staff_repo.create(
            db, name="Pin", pin_hash=hash_pin("old"), role=StaffRole.CASHIER.value
        )
        token = await _token_for(staff)
        # Token is valid before the PIN change.
        loaded = await get_current_staff(token, db)
        assert loaded.id == staff.id

        # Change PIN -> token_version bumps from 0 to 1.
        await StaffService.update_pin(
            db, staff_id=staff.id, new_pin="new", staff=staff
        )

        # Old token must now be rejected.
        with pytest.raises(HTTPException) as exc:
            await get_current_staff(token, db)
        assert exc.value.status_code == 401

    async def test_token_rejected_after_deactivation(
        self, db: AsyncSession
    ) -> None:
        staff = await staff_repo.create(
            db, name="Deact", pin_hash=hash_pin("1234"), role=StaffRole.CASHIER.value
        )
        token = await _token_for(staff)
        loaded = await get_current_staff(token, db)
        assert loaded.id == staff.id

        await StaffService.deactivate(db, staff_id=staff.id, staff=staff)

        with pytest.raises(HTTPException) as exc:
            await get_current_staff(token, db)
        assert exc.value.status_code == 401
