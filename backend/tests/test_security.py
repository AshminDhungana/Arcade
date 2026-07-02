"""Tests for backend.core.security.

Covers: PIN hashing (Argon2id), JWT encode/decode, brute-force rate limiting,
lockout, token_version invalidation, and role dependencies.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError

from backend.core.security import (
    create_access_token,
    decode_access_token,
    get_current_staff,
    hash_pin,
    is_ip_locked,
    record_failed_attempt,
    require_admin,
    require_cashier,
    reset_failed_attempts,
    verify_pin,
)
from backend.models._enums import StaffRole
from backend.models.staff import Staff


def test_hash_pin_returns_different_hash_each_time() -> None:
    """Argon2id salts ensure the same PIN produces different hashes."""
    pin = "1234"
    h1 = hash_pin(pin)
    h2 = hash_pin(pin)
    assert h1 != h2
    assert h1.startswith("$argon2id$")
    assert h2.startswith("$argon2id$")


def test_verify_pin_correct_and_incorrect() -> None:
    """verify_pin returns True for correct PIN, False for wrong PIN."""
    pin = "1234"
    h = hash_pin(pin)

    assert verify_pin("1234", h) is True
    assert verify_pin("9999", h) is False
    assert verify_pin("", h) is False


# ---------------------------------------------------------------------------
# JWT Tests
# ---------------------------------------------------------------------------


def test_create_access_token_round_trip() -> None:
    """Token encodes and decodes correctly with all claims."""
    token = create_access_token("staff_001", "ADMIN", token_version=3)
    payload = decode_access_token(token)

    assert payload["sub"] == "staff_001"
    assert payload["role"] == "ADMIN"
    assert payload["token_version"] == 3
    assert "exp" in payload


def test_decode_access_token_rejects_expired_token() -> None:
    """Expired token raises ExpiredSignatureError."""
    # Create a token that expired 1 second ago
    token = create_access_token("staff_001", "ADMIN", token_version=1, expires_delta=-1)
    with pytest.raises(ExpiredSignatureError):
        decode_access_token(token)


def test_decode_access_token_rejects_tampered_token() -> None:
    """Tampered signature raises JWTError."""
    token = create_access_token("staff_001", "ADMIN", token_version=1)
    tampered = token[:-10] + "tamper1234"  # noqa: S105
    with pytest.raises(JWTError):
        decode_access_token(tampered)


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Brute-force: 5 failures -> 15-minute lockout by IP."""

    def test_fresh_ip_not_locked(self) -> None:
        locked, remaining = is_ip_locked("192.168.1.10")
        assert locked is False
        assert remaining == 0

    def test_four_failed_attempts_not_locked(self) -> None:
        for _ in range(4):
            locked, _ = record_failed_attempt("192.168.1.11")
            assert locked is False

        locked, remaining = is_ip_locked("192.168.1.11")
        assert locked is False
        assert remaining == 0

    def test_fifth_failed_attempt_triggers_lockout(self) -> None:
        for i in range(4):
            locked, _ = record_failed_attempt("192.168.1.12")
            assert locked is False, f"attempt {i + 1}"

        locked, remaining = record_failed_attempt("192.168.1.12")
        assert locked is True
        assert remaining > 0
        assert remaining <= 15 * 60

    def test_reset_failed_attempts_clears_lockout(self) -> None:
        for _ in range(5):
            locked, _ = record_failed_attempt("192.168.1.13")

        assert locked is True
        reset_failed_attempts("192.168.1.13")
        locked2, _ = is_ip_locked("192.168.1.13")
        assert locked2 is False

    def test_different_ips_are_independent(self) -> None:
        for _ in range(5):
            record_failed_attempt("10.0.0.1")

        locked_a, _ = is_ip_locked("10.0.0.1")
        locked_b, _ = is_ip_locked("10.0.0.2")
        assert locked_a is True
        assert locked_b is False


# ---------------------------------------------------------------------------
# Auth Dependency Tests
# ---------------------------------------------------------------------------


class _FakeResult:
    def __init__(self, staff_list: list[Staff]) -> None:
        self._scalars = staff_list

    def scalars(self) -> _FakeResult:
        return self

    def first(self) -> Staff | None:
        return self._scalars[0] if self._scalars else None


class FakeDB:
    def __init__(self, staff: Staff | None) -> None:
        self._staff = staff

    async def execute(self, stmt: Any) -> _FakeResult:  # noqa: ANN401
        del stmt  # unused but matches AsyncSession signature
        return _FakeResult([self._staff] if self._staff is not None else [])


class TestGetCurrentStaff:
    async def test_valid_token_returns_staff(self) -> None:
        staff = Staff(
            id="staff_001",
            name="Alice",
            role=StaffRole.ADMIN,
            pin_hash="",
            token_version=7,
            is_active=True,
        )
        token = create_access_token("staff_001", "ADMIN", token_version=7)
        result = await get_current_staff(token, FakeDB(staff))  # type: ignore[arg-type]
        assert result.id == "staff_001"
        assert result.role == StaffRole.ADMIN

    async def test_stale_token_version_raises_401(self) -> None:
        staff = Staff(
            id="staff_002",
            name="Bob",
            role=StaffRole.CASHIER,
            pin_hash="",
            token_version=2,
            is_active=True,
        )
        token = create_access_token("staff_002", "CASHIER", token_version=1)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_staff(token, FakeDB(staff))  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401

    async def test_inactive_staff_raises_401(self) -> None:
        staff = Staff(
            id="staff_003",
            name="Charlie",
            role=StaffRole.ADMIN,
            pin_hash="",
            token_version=1,
            is_active=False,
        )
        token = create_access_token("staff_003", "ADMIN", token_version=1)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_staff(token, FakeDB(staff))  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401

    async def test_malformed_token_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_staff("not-a-token", FakeDB(None))  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401


class TestRoleDependencies:
    def test_require_admin_allows_admin(self) -> None:
        staff = Staff(
            id="s1", name="Admin", role=StaffRole.ADMIN, pin_hash="", is_active=True
        )
        result = require_admin(staff)
        assert result is staff

    def test_require_admin_rejects_cashier(self) -> None:
        staff = Staff(
            id="s2",
            name="Cashier",
            role=StaffRole.CASHIER,
            pin_hash="",
            is_active=True,
        )
        with pytest.raises(HTTPException) as exc_info:
            require_admin(staff)
        assert exc_info.value.status_code == 403

    def test_require_cashier_allows_both(self) -> None:
        admin = Staff(
            id="s3", name="Admin", role=StaffRole.ADMIN, pin_hash="", is_active=True
        )
        cashier = Staff(
            id="s4",
            name="Cashier",
            role=StaffRole.CASHIER,
            pin_hash="",
            is_active=True,
        )
        assert require_cashier(admin) is admin
        assert require_cashier(cashier) is cashier

    def test_require_cashier_rejects_invalid_role(self) -> None:
        # Build a duck-type mock since the enum prevents an invalid role.
        class _FakeStaff:
            role = "INVALID"

        with pytest.raises(HTTPException) as exc_info:
            require_cashier(_FakeStaff())  # type: ignore[arg-type]
        assert exc_info.value.status_code == 403
