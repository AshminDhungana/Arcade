"""Integration tests for the staff authentication API.

Covers: login success/failure, rate limiting (5 attempts → 15-minute lockout),
inactive staff rejection, token refresh, and logout.
"""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.security import create_access_token, hash_pin, is_ip_locked
from backend.models._enums import StaffRole
from backend.repositories import staff_repo
from backend.services import auth_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB.

    Using a file-based DB instead of in-memory avoids aiosqlite threading issues
    during test cleanup (Windows fatal exception on engine.dispose()).
    """
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


# ---------------------------------------------------------------------------
# Service-level tests: login()
# ---------------------------------------------------------------------------


class TestLoginService:
    async def test_login_success(self, db: AsyncSession) -> None:
        staff = await staff_repo.create(
            db, name="Alice", pin_hash=hash_pin("1234"), role="ADMIN"
        )
        result = await auth_service.login(db, staff.id, "1234", "127.0.0.1")
        assert result.access_token
        assert result.token_type == "bearer"
        assert result.expires_in == 28800
        assert result.staff.name == "Alice"

    async def test_login_wrong_pin(self, db: AsyncSession) -> None:
        staff = await staff_repo.create(
            db, name="Bob", pin_hash=hash_pin("9999"), role="CASHIER"
        )
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "1111", "10.0.0.1")
        assert exc_info.value.status_code == 401

    async def test_login_nonexistent_staff(self, db: AsyncSession) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, "non-existent-id", "1234", "192.168.1.1")
        assert exc_info.value.status_code == 401

    async def test_login_inactive_staff(self, db: AsyncSession) -> None:
        staff = await staff_repo.create(
            db, name="Charlie", pin_hash=hash_pin("0000"), role="CASHIER"
        )
        staff.is_active = False
        await db.flush()
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "0000", "192.168.1.2")
        assert exc_info.value.status_code == 401

    async def test_rate_limit_locks_after_5_failures(self, db: AsyncSession) -> None:
        staff = await staff_repo.create(
            db, name="Rate Test", pin_hash=hash_pin("correct"), role="ADMIN"
        )
        ip = "192.168.1.100"
        for i in range(4):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.login(db, staff.id, "wrong", ip)
            assert exc_info.value.status_code == 401, f"attempt {i + 1}"

        # 5th attempt triggers lockout
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "wrong", ip)
        assert exc_info.value.status_code == 429

        # Even correct PIN is blocked
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "correct", ip)
        assert exc_info.value.status_code == 429

    async def test_rate_limit_resets_on_success(self, db: AsyncSession) -> None:
        staff = await staff_repo.create(
            db, name="Reset Test", pin_hash=hash_pin("pass123"), role="ADMIN"
        )
        ip = "192.168.1.101"
        # 3 failures
        for _ in range(3):
            try:
                await auth_service.login(db, staff.id, "wrong", ip)
            except HTTPException:
                pass
        # Success resets counter
        result = await auth_service.login(db, staff.id, "pass123", ip)
        assert result.access_token
        # 3 more failures shouldn't lock out since counter was reset
        for _ in range(3):
            try:
                await auth_service.login(db, staff.id, "wrong", ip)
            except HTTPException:
                pass
        # Should still be unlocked (only 3 failures after reset)
        locked, _ = is_ip_locked(ip)
        assert locked is False


# ---------------------------------------------------------------------------
# Service-level tests: refresh_token()
# ---------------------------------------------------------------------------


class TestRefreshToken:
    async def test_refresh_valid_token(self, db: AsyncSession) -> None:
        staff = await staff_repo.create(
            db, name="Refresh Test", pin_hash=hash_pin("refresh"), role="ADMIN"
        )
        old_token = create_access_token(staff.id, str(staff.role), staff.token_version)

        result = await auth_service.refresh_token(old_token, db)
        assert result.access_token
        assert result.access_token != old_token
        assert result.staff.name == "Refresh Test"

    async def test_refresh_invalid_token(self, db: AsyncSession) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token("bad-token", db)
        assert exc_info.value.status_code == 401

    async def test_refresh_stale_token_version(self, db: AsyncSession) -> None:
        staff = await staff_repo.create(
            db, name="Stale Test", pin_hash=hash_pin("stale"), role="ADMIN"
        )
        old_token = create_access_token(staff.id, str(staff.role), 99)  # stale version
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(old_token, db)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Router-level tests (via TestClient)
# ---------------------------------------------------------------------------


class TestAuthRouter:
    """Full request/response cycle through FastAPI's TestClient."""

    @pytest.fixture
    def client(self) -> Iterator[TestClient]:
        from fastapi.testclient import TestClient

        from backend.api.deps import get_current_staff as _get_current_staff
        from backend.main import app

        # Save original to restore later
        original = app.dependency_overrides.get(_get_current_staff)

        class _MockStaff:
            id = "mock-staff-id"
            name = "Mock Admin"
            is_active = True
            token_version = 0
            role = StaffRole.ADMIN

        app.dependency_overrides[_get_current_staff] = lambda: _MockStaff()
        with TestClient(app) as c:
            yield c
        if original is None:
            app.dependency_overrides.pop(_get_current_staff, None)
        else:
            app.dependency_overrides[_get_current_staff] = original

    def test_refresh_endpoint_invalid_token(self, client: TestClient) -> None:
        resp = client.post(
            "/api/auth/refresh",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401

    def test_logout_endpoint(self, client: TestClient) -> None:
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer mock-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Logged out successfully"
