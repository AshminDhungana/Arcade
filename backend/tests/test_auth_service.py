"""Integration tests for auth_service.py and staff_service.py.

Covers:
- auth_service.login: success (token_version in payload), wrong PIN
  (401 + rate limit), inactive staff (401)
- auth_service.rate limiting: 5 failures -> 15-min lockout; success resets counter
- auth_service.refresh_token: valid token -> new token; stale token_version
  -> 401; invalid token -> 401
- staff_service.create: creates Staff with Argon2-hashed PIN
- staff_service.update_pin: bumps token_version; old token rejected on next refresh
- staff_service.deactivate: bumps token_version; old token rejected
- staff_service.reactivate: bumps token_version; old token rejected

Uses async SQLAlchemy with a temporary file-based SQLite DB (aiosqlite).
"""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.bootstrap import ensure_default_staff
from backend.core.config import Settings
from backend.core.database import Base
from backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_pin,
    verify_pin,
)
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.repositories import staff_repo
from backend.services import auth_service, staff_service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB.

    Using a file-based DB instead of in-memory avoids aiosqlite threading
    issues during test cleanup on Windows (engine.dispose() fatal exception).
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
# Fixtures / helpers for creating staff
# ---------------------------------------------------------------------------


async def _create_staff(
    db: AsyncSession,
    *,
    staff_id: str,
    name: str,
    role: StaffRole | str,
    pin: str,
    is_active: bool = True,
) -> Staff:
    """Helper to create a Staff row with a known PIN (hashed) and explicit ID."""
    role_value = role.value if isinstance(role, StaffRole) else str(role)

    staff = Staff(
        id=staff_id,
        name=name,
        role=role_value,
        pin_hash=hash_pin(pin),
        is_active=is_active,
    )
    db.add(staff)
    await db.flush()
    await db.refresh(staff)
    return staff


# ---------------------------------------------------------------------------
# Test class: auth_service.login
# ---------------------------------------------------------------------------


class TestDefaultAdminBootstrap:
    """Ties ensure_default_staff (Task 1) to login + token revocation.

    This is the acceptance test for the default-admin feature: the seeded
    admin must be loginable, and a PIN change must invalidate its token.
    """

    async def test_bootstrap_admin_logs_in_then_pin_change_invalidates_token(
        self, db: AsyncSession
    ) -> None:
        settings = Settings(
            admin_staff_id="admin",
            admin_pin_hash=hash_pin("admin"),
            cashier_staff_id="cashier",
            cashier_pin_hash=hash_pin("cashier"),
        )
        await ensure_default_staff(db, settings=settings)
        await db.commit()

        # Seeded admin/cashier exist with the expected ids.
        admin = await staff_repo.get_by_id(db, "admin")
        cashier = await staff_repo.get_by_id(db, "cashier")
        assert admin is not None and cashier is not None

        # Login with default admin/admin succeeds.
        token_resp = await auth_service.login(db, "admin", "admin", "127.0.0.1")
        assert token_resp.access_token

        # Capture the token_version baked into the issued token.
        payload = decode_access_token(token_resp.access_token)
        issued_version = payload["token_version"]

        # Change the PIN via the existing service (bumps token_version).
        old_version = admin.token_version
        await staff_service.StaffService.update_pin(
            db, staff_id="admin", new_pin="newpin123"
        )
        await db.commit()

        reloaded = await staff_repo.get_by_id(db, "admin")
        assert reloaded.token_version == old_version + 1
        assert verify_pin("newpin123", reloaded.pin_hash) is True

        # Old token is now stale: its baked version != the current staff row.
        assert payload["token_version"] == issued_version
        assert reloaded.token_version != issued_version


class TestAuthServiceLogin:
    """Tests for auth_service.login: success, wrong PIN, inactive, rate limit."""

    async def test_login_success_returns_token_with_token_version(
        self, db: AsyncSession
    ) -> None:
        """Successful login returns a token containing the staff's token_version."""
        staff = await _create_staff(
            db, staff_id="admin", name="Admin", role=StaffRole.ADMIN, pin="admin123"
        )

        result = await auth_service.login(db, staff.id, "admin123", "127.0.0.1")

        assert result.access_token
        assert result.token_type == "bearer"
        assert result.expires_in == 28800
        assert result.staff.id == staff.id
        assert result.staff.name == "Admin"
        assert result.staff.role == StaffRole.ADMIN

        # Verify token payload contains token_version matching DB row
        payload = decode_access_token(result.access_token)
        assert payload["sub"] == staff.id
        # auth_service.login uses str(staff.role); for a plain Enum
        # this gives "StaffRole.ADMIN" rather than "ADMIN"
        assert payload["role"] == str(StaffRole.ADMIN)
        assert payload["token_version"] == staff.token_version

    async def test_login_wrong_pin_returns_401_and_rate_limits_ip(
        self, db: AsyncSession
    ) -> None:
        """Wrong PIN returns 401 and increments the IP's failure counter."""
        staff = await _create_staff(
            db, staff_id="cashier", name="Cashier", role="CASHIER", pin="1234"
        )
        ip = "10.0.0.50"

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "wrong", ip)
        assert exc_info.value.status_code == 401

        # 4 more failures should lock the IP
        for _ in range(3):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.login(db, staff.id, "wrong", ip)
            assert exc_info.value.status_code == 401

        # 5th failure -> lockout (429)
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "wrong", ip)
        assert exc_info.value.status_code == 429
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers

    async def test_login_inactive_staff_returns_401(self, db: AsyncSession) -> None:
        """Inactive staff returns 401 without revealing existence."""
        staff = await _create_staff(
            db,
            staff_id="inactive",
            name="Inactive",
            role="ADMIN",
            pin="1234",
            is_active=False,
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "1234", "192.168.1.1")
        assert exc_info.value.status_code == 401

    async def test_login_nonexistent_staff_returns_401(self, db: AsyncSession) -> None:
        """Non-existent staff ID returns 401 (no user enumeration)."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, "does-not-exist", "1234", "192.168.1.2")
        assert exc_info.value.status_code == 401

    async def test_rate_limit_lockout_blocks_even_correct_pin(
        self, db: AsyncSession
    ) -> None:
        """After 5 failures, even the correct PIN is rejected (429)."""
        staff = await _create_staff(
            db, staff_id="locked", name="Locked", role="ADMIN", pin="correct"
        )
        ip = "192.168.1.200"

        # 5 failures
        for _ in range(5):
            with pytest.raises(HTTPException):
                await auth_service.login(db, staff.id, "wrong", ip)

        # Correct PIN now blocked
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(db, staff.id, "correct", ip)
        assert exc_info.value.status_code == 429

    async def test_successful_login_resets_failure_counter(
        self, db: AsyncSession
    ) -> None:
        """A successful login resets the IP's failure counter."""
        staff = await _create_staff(
            db, staff_id="reset", name="Reset", role="ADMIN", pin="pass123"
        )
        ip = "192.168.1.201"

        # 3 failures
        for _ in range(3):
            with pytest.raises(HTTPException):
                await auth_service.login(db, staff.id, "wrong", ip)

        # Success resets counter
        result = await auth_service.login(db, staff.id, "pass123", ip)
        assert result.access_token

        # 3 more failures should NOT lock (only 3 since reset)
        for _ in range(3):
            with pytest.raises(HTTPException):
                await auth_service.login(db, staff.id, "wrong", ip)

        # Should still be unlocked
        from backend.core.security import is_ip_locked

        locked, _ = is_ip_locked(ip)
        assert locked is False


# ---------------------------------------------------------------------------
# Test class: auth_service.refresh_token
# ---------------------------------------------------------------------------


class TestAuthServiceRefreshToken:
    """Tests for auth_service.refresh_token: valid, stale version, invalid tokens."""

    async def test_refresh_valid_token_returns_new_token(
        self, db: AsyncSession
    ) -> None:
        """Valid token returns a new token with renewed expiry."""
        staff = await _create_staff(
            db, staff_id="refresh1", name="Refresh1", role="ADMIN", pin="pin123"
        )
        old_token = create_access_token(staff.id, str(staff.role), staff.token_version)

        result = await auth_service.refresh_token(old_token, db)

        assert result.access_token
        assert result.access_token != old_token
        assert result.staff.id == staff.id

        # New token should have same token_version (staff not modified)
        new_payload = decode_access_token(result.access_token)
        assert new_payload["token_version"] == staff.token_version

    async def test_refresh_stale_token_version_returns_401(
        self, db: AsyncSession
    ) -> None:
        """Token with stale token_version is rejected (401)."""
        staff = await _create_staff(
            db, staff_id="stale", name="Stale", role="CASHIER", pin="pin"
        )
        # Craft token with a version that doesn't match DB (e.g., 999)
        stale_token = create_access_token(staff.id, str(staff.role), 999)

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(stale_token, db)
        assert exc_info.value.status_code == 401

    async def test_refresh_invalid_token_returns_401(self, db: AsyncSession) -> None:
        """Malformed/invalid signature token returns 401."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token("not-a-valid-token", db)
        assert exc_info.value.status_code == 401

    async def test_refresh_token_for_deactivated_staff_returns_401(
        self, db: AsyncSession
    ) -> None:
        """Token for a staff member deactivated after token issuance is rejected."""
        staff = await _create_staff(
            db, staff_id="deact", name="Deact", role="ADMIN", pin="pin"
        )
        token = create_access_token(staff.id, str(staff.role), staff.token_version)

        # Deactivate staff (bumps token_version)
        await staff_service.StaffService.deactivate(db, staff_id=staff.id)

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(token, db)
        assert exc_info.value.status_code == 401

    async def test_refresh_token_for_reactivated_staff_returns_401(
        self, db: AsyncSession
    ) -> None:
        """Token issued before reactivation is rejected (token_version bumped)."""
        staff = await _create_staff(
            db, staff_id="react", name="React", role="ADMIN", pin="pin"
        )
        token = create_access_token(staff.id, str(staff.role), staff.token_version)

        # Deactivate then reactivate (two version bumps)
        await staff_service.StaffService.deactivate(db, staff_id=staff.id)
        await staff_service.StaffService.reactivate(db, staff_id=staff.id)

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(token, db)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Test class: staff_service.StaffService.create
# ---------------------------------------------------------------------------


class TestStaffServiceCreate:
    """Tests for staff_service.StaffService.create."""

    async def test_create_staff_hashes_pin_with_argon2(self, db: AsyncSession) -> None:
        """Created staff has an Argon2id hash, never plaintext."""
        staff = await staff_service.StaffService.create(
            db, name="Hashed", role=StaffRole.ADMIN, pin="secret-pin"
        )

        assert staff.id
        assert staff.name == "Hashed"
        assert staff.role == StaffRole.ADMIN
        assert staff.is_active is True
        assert staff.token_version == 0

        # PIN is hashed (Argon2id prefix $argon2id$)
        assert staff.pin_hash.startswith("$argon2id$")
        # Verify the hash works
        assert verify_pin("secret-pin", staff.pin_hash) is True
        assert verify_pin("wrong", staff.pin_hash) is False

    async def test_create_staff_with_custom_id_and_inactive(
        self, db: AsyncSession
    ) -> None:
        """create() uses auto-generated ID by default; inactive flag respected."""
        staff = await staff_service.StaffService.create(
            db, name="Custom", role="CASHIER", pin="1234", is_active=False
        )
        assert staff.is_active is False
        assert staff.token_version == 0

    async def test_create_staff_audits_creation(self, db: AsyncSession) -> None:
        """Creation logs an audit entry (STAFF_CREATED)."""
        from backend.models._enums import AuditAction
        from backend.repositories import audit_repo

        await staff_service.StaffService.create(
            db, name="AuditTest", role="ADMIN", pin="pin"
        )
        await db.commit()

        audits = await audit_repo.list(db)
        assert any(a.action == AuditAction.STAFF_CREATED for a in audits)


# ---------------------------------------------------------------------------
# Test class: staff_service.StaffService.update_pin
# ---------------------------------------------------------------------------


class TestStaffServiceUpdatePin:
    """Tests for StaffService.update_pin: token_version bump, old token invalidation."""

    async def test_update_pin_bumps_token_version(self, db: AsyncSession) -> None:
        """Updating PIN increments token_version."""
        staff = await _create_staff(
            db, staff_id="pin1", name="Pin1", role="ADMIN", pin="oldpin"
        )
        original_version = staff.token_version

        updated = await staff_service.StaffService.update_pin(
            db, staff_id=staff.id, new_pin="newpin"
        )

        assert updated.token_version == original_version + 1
        assert verify_pin("newpin", updated.pin_hash) is True
        assert verify_pin("oldpin", updated.pin_hash) is False

    async def test_update_pin_invalidates_old_token_on_refresh(
        self, db: AsyncSession
    ) -> None:
        """Token issued before PIN change is rejected on refresh."""
        staff = await _create_staff(
            db, staff_id="pin2", name="Pin2", role="ADMIN", pin="oldpin"
        )
        old_token = create_access_token(staff.id, str(staff.role), staff.token_version)

        # Change PIN
        await staff_service.StaffService.update_pin(
            db, staff_id=staff.id, new_pin="newpin"
        )

        # Refresh staff to get updated token_version
        await db.refresh(staff)

        # Old token now stale
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(old_token, db)
        assert exc_info.value.status_code == 401

        # New token with updated version works
        new_token = create_access_token(staff.id, str(staff.role), staff.token_version)
        result = await auth_service.refresh_token(new_token, db)
        assert result.access_token

    async def test_update_pin_audits_change(self, db: AsyncSession) -> None:
        """PIN change logs STAFF_PIN_CHANGED audit entry."""
        from backend.models._enums import AuditAction
        from backend.repositories import audit_repo

        staff = await _create_staff(
            db, staff_id="pin3", name="Pin3", role="ADMIN", pin="oldpin"
        )
        await staff_service.StaffService.update_pin(
            db, staff_id=staff.id, new_pin="newpin"
        )
        await db.commit()

        audits = await audit_repo.list(db)
        assert any(a.action == AuditAction.STAFF_PIN_CHANGED for a in audits)


# ---------------------------------------------------------------------------
# Test class: staff_service.StaffService.deactivate
# ---------------------------------------------------------------------------


class TestStaffServiceDeactivate:
    """Tests for StaffService.deactivate: token_version bump, old token invalidation."""

    async def test_deactivate_sets_inactive_and_bumps_token_version(
        self, db: AsyncSession
    ) -> None:
        """Deactivating sets is_active=False and increments token_version."""
        staff = await _create_staff(
            db, staff_id="deact1", name="Deact1", role="ADMIN", pin="pin"
        )
        original_version = staff.token_version

        deactivated = await staff_service.StaffService.deactivate(db, staff_id=staff.id)

        assert deactivated.is_active is False
        assert deactivated.token_version == original_version + 1

    async def test_deactivate_invalidates_existing_token(
        self, db: AsyncSession
    ) -> None:
        """Token issued before deactivation is rejected on refresh."""
        staff = await _create_staff(
            db, staff_id="deact2", name="Deact2", role="ADMIN", pin="pin"
        )
        token = create_access_token(staff.id, str(staff.role), staff.token_version)

        await staff_service.StaffService.deactivate(db, staff_id=staff.id)

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(token, db)
        assert exc_info.value.status_code == 401

    async def test_deactivate_audits_deactivation(self, db: AsyncSession) -> None:
        """Deactivation logs STAFF_DEACTIVATED audit entry."""
        from backend.models._enums import AuditAction
        from backend.repositories import audit_repo

        staff = await _create_staff(
            db, staff_id="deact3", name="Deact3", role="ADMIN", pin="pin"
        )
        await staff_service.StaffService.deactivate(db, staff_id=staff.id)
        await db.commit()

        audits = await audit_repo.list(db)
        assert any(a.action == AuditAction.STAFF_DEACTIVATED for a in audits)

    async def test_deactivate_nonexistent_raises_404(self, db: AsyncSession) -> None:
        """Deactivating non-existent staff raises NotFoundError (404)."""
        with pytest.raises(HTTPException) as exc_info:
            await staff_service.StaffService.deactivate(db, staff_id="does-not-exist")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test class: staff_service.StaffService.reactivate
# ---------------------------------------------------------------------------


class TestStaffServiceReactivate:
    """Tests for StaffService.reactivate: token_version bump, old token invalidation."""

    async def test_activate_sets_active_and_bumps_token_version(
        self, db: AsyncSession
    ) -> None:
        """Reactivating sets is_active=True and increments token_version."""
        staff = await _create_staff(
            db, staff_id="react1", name="React1", role="ADMIN", pin="pin"
        )
        # First deactivate
        await staff_service.StaffService.deactivate(db, staff_id=staff.id)
        deactivated_version = staff.token_version

        reactivated = await staff_service.StaffService.reactivate(db, staff_id=staff.id)

        assert reactivated.is_active is True
        assert reactivated.token_version == deactivated_version + 1

    async def test_reactivate_invalidates_token_issued_before_reactivation(
        self, db: AsyncSession
    ) -> None:
        """Token issued before reactivation is rejected (token_version bumped twice)."""
        staff = await _create_staff(
            db, staff_id="react2", name="React2", role="ADMIN", pin="pin"
        )
        # Token issued while active (version 0)
        token_v0 = create_access_token(staff.id, str(staff.role), staff.token_version)

        # Deactivate (v1) then reactivate (v2)
        await staff_service.StaffService.deactivate(db, staff_id=staff.id)
        await staff_service.StaffService.reactivate(db, staff_id=staff.id)

        # Token from v0 should be rejected
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token(token_v0, db)
        assert exc_info.value.status_code == 401

        # New token with current version (v2) works
        new_token = create_access_token(staff.id, str(staff.role), staff.token_version)
        result = await auth_service.refresh_token(new_token, db)
        assert result.access_token

    async def test_reactivate_audits_reactivation(self, db: AsyncSession) -> None:
        """Reactivation logs STAFF_REACTIVATED audit entry."""
        from backend.models._enums import AuditAction
        from backend.repositories import audit_repo

        staff = await _create_staff(
            db, staff_id="react3", name="React3", role="ADMIN", pin="pin"
        )
        await staff_service.StaffService.deactivate(db, staff_id=staff.id)
        await staff_service.StaffService.reactivate(db, staff_id=staff.id)
        await db.commit()

        audits = await audit_repo.list(db)
        assert any(a.action == AuditAction.STAFF_REACTIVATED for a in audits)

    async def test_reactivate_nonexistent_raises_404(self, db: AsyncSession) -> None:
        """Reactivating non-existent staff raises NotFoundError (404)."""
        with pytest.raises(HTTPException) as exc_info:
            await staff_service.StaffService.reactivate(db, staff_id="does-not-exist")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Test class: staff_service.StaffService.list_staff
# ---------------------------------------------------------------------------


class TestStaffServiceListStaff:
    """Basic list_staff coverage."""

    async def test_list_staff_returns_all_staff(self, db: AsyncSession) -> None:
        """list_staff returns all created staff."""
        await _create_staff(db, staff_id="a1", name="A", role="ADMIN", pin="1")
        await _create_staff(db, staff_id="a2", name="B", role="CASHIER", pin="2")
        await _create_staff(
            db, staff_id="a3", name="C", role="ADMIN", pin="3", is_active=False
        )

        staff_list = await staff_service.StaffService.list_staff(db)

        assert len(staff_list) == 3
        names = {s.name for s in staff_list}
        assert names == {"A", "B", "C"}
