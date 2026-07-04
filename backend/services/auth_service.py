"""Auth Service — PIN login, rate limiting, and token refresh.

All public functions are ``async def`` and accept ``db: AsyncSession``
as their first parameter.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import (
    create_access_token,
    decode_access_token,
    is_ip_locked,
    record_failed_attempt,
    reset_failed_attempts,
    verify_pin,
)
from backend.repositories import audit_repo, staff_repo
from backend.schemas.staff import StaffResponse, TokenResponse


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """SQLite sometimes strips timezone info from ``DateTime(timezone=True)``.

    Re-attach UTC when it is missing so Pydantic's ``AwareDatetime``
    validates cleanly.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _staff_to_response(staff) -> StaffResponse:  # type: ignore[no-untyped-def]
    """Normalise ``updated_at`` timezone and build a ``StaffResponse``."""
    staff.updated_at = _ensure_tz(staff.updated_at)
    return StaffResponse.model_validate(staff)


# Exposed for tests
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
_DEFAULT_JWT_EXPIRY = 28800  # 8 hours in seconds


class AuthError(HTTPException):
    """Base auth error."""


class InvalidCredentialsError(HTTPException):
    """Raised when credentials are invalid — always returns 401."""

    def __init__(self) -> None:
        super().__init__(status_code=401, detail="Invalid staff ID or PIN")


class RateLimitedError(HTTPException):
    """Raised when an IP is rate-limited."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            status_code=429,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def login(
    db: AsyncSession,
    staff_id: str,
    pin: str,
    client_ip: str,
) -> TokenResponse:
    """Authenticate a staff member with *staff_id* and *pin*.

    On success, returns a JWT and resets failed attempts for *client_ip*.
    On failure, records the failed attempt.

    :raises RateLimitedError:   If the IP is locked out.
    :raises InvalidCredentialsError: If staff not found, inactive, or PIN is wrong.
    """
    # 1. Rate-limit check
    locked, retry_after = is_ip_locked(client_ip)
    if locked:
        raise RateLimitedError(retry_after)

    # 2. Load staff from DB
    staff = await staff_repo.get_by_id(db, staff_id)
    if staff is None:
        record_failed_attempt(client_ip)
        raise InvalidCredentialsError()

    # 3. Check active
    if not staff.is_active:
        record_failed_attempt(client_ip)
        raise InvalidCredentialsError()

    # 4. Verify PIN (Argon2id)
    if not verify_pin(pin, staff.pin_hash):
        locked, retry_after = record_failed_attempt(client_ip)
        if locked:
            raise RateLimitedError(retry_after)
        raise InvalidCredentialsError()

    # 5. Success — clear failures and issue token
    reset_failed_attempts(client_ip)
    token = create_access_token(
        staff.id,
        role=str(staff.role),
        token_version=staff.token_version,
    )

    # 6. Audit log
    await audit_repo.create(
        db,
        action="STAFF_LOGIN",
        entity_type="staff",
        entity_id=staff.id,
        staff_id=staff.id,
        detail=f"Login from {client_ip}",
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",  # noqa: S106
        expires_in=_DEFAULT_JWT_EXPIRY,
        staff=_staff_to_response(staff),
    )


async def refresh_token(token: str, db: AsyncSession) -> TokenResponse:
    """Validate an existing token and issue a new one with renewed expiry.

    Validates ``token_version`` against the DB to ensure the token
    has not been invalidated by a PIN change or deactivation.

    :raises HTTPException(401): If the token is invalid, expired, or the
        staff member has been deactivated / PIN changed.
    """
    # 1. Decode existing token (jose will raise on expiry/bad sig)
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        ) from None

    staff_id = payload.get("sub")
    token_version = payload.get("token_version")
    if not isinstance(staff_id, str) or not isinstance(token_version, int):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # 2. Re-validate against DB
    staff = await staff_repo.get_by_id(db, staff_id)
    if staff is None or not staff.is_active or staff.token_version != token_version:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # 3. Issue fresh token
    new_token = create_access_token(
        staff.id,
        role=str(staff.role),
        token_version=staff.token_version,
    )

    return TokenResponse(
        access_token=new_token,
        token_type="bearer",  # noqa: S106
        expires_in=_DEFAULT_JWT_EXPIRY,
        staff=_staff_to_response(staff),
    )
