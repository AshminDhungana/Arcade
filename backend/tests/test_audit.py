"""Tests for the AuditService and the /api/audit router."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff
from backend.core.database import Base
from backend.main import app
from backend.models._enums import AuditAction

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on an in-memory SQLite DB."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


def _make_mock_staff(role="ADMIN"):
    from backend.models._enums import StaffRole

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock Admin"
        is_active = True
        token_version = 0

    obj = _MockStaff()
    if isinstance(role, str):
        obj.role = StaffRole(role)
    else:
        obj.role = role
    return obj


@pytest.fixture
def client() -> Iterator[TestClient]:
    mock_staff = _make_mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_current_staff, None)


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestAuditService:
    async def test_log_creates_entry(self, db: AsyncSession) -> None:
        from backend.services import audit_service

        log = await audit_service.log(
            db,
            action=AuditAction.SESSION_START,
            entity_type="session",
            entity_id="s1",
            staff_id="staff-1",
            detail="started seat 1",
        )
        assert log.id is not None
        assert log.action == AuditAction.SESSION_START
        assert log.entity_type == "session"
        assert log.entity_id == "s1"

    async def test_list_logs_without_filters(self, db: AsyncSession) -> None:
        from backend.services import audit_service

        await audit_service.log(
            db, action=AuditAction.SESSION_START, entity_type="session", entity_id="s1"
        )
        await audit_service.log(
            db, action=AuditAction.SESSION_END, entity_type="session", entity_id="s1"
        )
        await db.commit()
        logs = await audit_service.list_logs(
            db,
            start_date=None,  # type: ignore[arg-type]
            end_date=None,  # type: ignore[arg-type]
            action=None,  # type: ignore[arg-type]
            staff_id=None,  # type: ignore[arg-type]
            limit=10,
            offset=0,
        )
        assert len(logs) == 2

    async def test_list_logs_with_action_filter(self, db: AsyncSession) -> None:
        from backend.services import audit_service

        await audit_service.log(
            db, action=AuditAction.SESSION_START, entity_type="session", entity_id="s1"
        )
        await audit_service.log(
            db, action=AuditAction.SESSION_END, entity_type="session", entity_id="s1"
        )
        await db.commit()
        logs = await audit_service.list_logs(
            db,
            start_date=None,  # type: ignore[arg-type]
            end_date=None,  # type: ignore[arg-type]
            action=AuditAction.SESSION_START,
            staff_id=None,  # type: ignore[arg-type]
            limit=10,
            offset=0,
        )
        assert len(logs) == 1
        assert logs[0].action == AuditAction.SESSION_START


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


def test_get_audit_logs_returns_200(client: TestClient) -> None:
    resp = client.get("/api/audit")
    assert resp.status_code == 200


def test_get_audit_logs_with_pagination(client: TestClient) -> None:
    resp = client.get("/api/audit?limit=5&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
