"""Tests for StaffService — create and list."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.security import hash_pin, verify_pin
from backend.models._enums import AuditAction, StaffRole
from backend.models.staff import Staff
from backend.repositories import staff_repo
from backend.services import audit_service
from backend.services.staff_service import NotFoundError, StaffService


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
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def actor(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db, name="Admin Actor", pin_hash=hash_pin("0000"), role=StaffRole.ADMIN.value
    )


class TestCreateStaff:
    async def test_create_sets_token_version_zero_and_hashes_pin(
        self, db: AsyncSession, actor: Staff
    ) -> None:
        staff = await StaffService.create(
            db, name="New Hire", role=StaffRole.CASHIER, pin="1234", staff=actor
        )
        assert staff.token_version == 0
        assert staff.is_active is True
        assert verify_pin("1234", staff.pin_hash) is True
        assert verify_pin("wrong", staff.pin_hash) is False

    async def test_create_audit_logged(self, db: AsyncSession, actor: Staff) -> None:
        staff = await StaffService.create(
            db, name="Audited", role=StaffRole.ADMIN, pin="5678", staff=actor
        )
        logs = await audit_service.list_logs(
            db, action=AuditAction.STAFF_CREATED, entity_id=staff.id
        )
        assert len(logs) == 1
        assert "Audited" in logs[0].detail

    async def test_create_inactive(self, db: AsyncSession, actor: Staff) -> None:
        staff = await StaffService.create(
            db,
            name="Inactive",
            role=StaffRole.CASHIER,
            pin="9999",
            is_active=False,
            staff=actor,
        )
        assert staff.is_active is False


class TestListStaff:
    async def test_list_returns_all(self, db: AsyncSession, actor: Staff) -> None:
        await staff_repo.create(
            db, name="A", pin_hash=hash_pin("1"), role=StaffRole.ADMIN.value
        )
        await staff_repo.create(
            db, name="B", pin_hash=hash_pin("1"), role=StaffRole.CASHIER.value
        )
        result = await StaffService.list_staff(db)
        assert len(result) >= 3  # actor + 2
        assert all(isinstance(s, Staff) for s in result)


class TestUpdatePin:
    async def test_update_pin_increments_token_version_and_rehashes(
        self, db: AsyncSession, actor: Staff
    ) -> None:
        staff = await staff_repo.create(
            db, name="Pin", pin_hash=hash_pin("oldpin"), role=StaffRole.CASHIER.value
        )
        updated = await StaffService.update_pin(
            db, staff_id=staff.id, new_pin="newpin", staff=actor
        )
        assert updated.token_version == 1
        assert verify_pin("newpin", updated.pin_hash) is True
        assert verify_pin("oldpin", updated.pin_hash) is False

    async def test_update_pin_audit_logged(
        self, db: AsyncSession, actor: Staff
    ) -> None:
        staff = await staff_repo.create(
            db, name="Pin2", pin_hash=hash_pin("oldpin"), role=StaffRole.CASHIER.value
        )
        await StaffService.update_pin(
            db, staff_id=staff.id, new_pin="newpin", staff=actor
        )
        logs = await audit_service.list_logs(
            db, action=AuditAction.STAFF_PIN_CHANGED, entity_id=staff.id
        )
        assert len(logs) == 1

    async def test_update_pin_not_found(self, db: AsyncSession, actor: Staff) -> None:
        with pytest.raises(NotFoundError) as exc:
            await StaffService.update_pin(
                db, staff_id="missing", new_pin="x", staff=actor
            )
        assert exc.value.status_code == 404
