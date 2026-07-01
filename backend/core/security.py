"""Security utilities: PIN hashing, JWT, rate limiting, and auth dependencies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_config
from backend.models._enums import StaffRole
from backend.models.staff import Staff

# ---------------------------------------------------------------------------
# Argon2id — OWASP-recommended parameters
# ---------------------------------------------------------------------------

_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=102400,
    parallelism=8,
    hash_len=32,
    salt_len=16,
)


def hash_pin(pin: str) -> str:
    """Hash a plaintext PIN with Argon2id."""
    return _hasher.hash(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Return True if *pin* matches *pin_hash*, else False."""
    try:
        _hasher.verify(pin_hash, pin)
    except VerifyMismatchError:
        return False
    else:
        return True


# ---------------------------------------------------------------------------
# JWT — HS256, 8-hour default expiry
# ---------------------------------------------------------------------------

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_SECONDS = 28800  # 8 hours


def create_access_token(
    staff_id: str,
    role: str,
    token_version: int,
    *,
    expires_delta: int | None = None,
) -> str:
    """Create a JWT access token for a staff member."""
    config = get_config()
    delta = timedelta(
        seconds=expires_delta if expires_delta is not None else _JWT_EXPIRY_SECONDS
    )
    payload = {
        "sub": staff_id,
        "role": role,
        "token_version": token_version,
        "exp": (datetime.now(UTC) + delta).timestamp(),
    }
    return str(jwt.encode(payload, config.jwt_secret, algorithm=_JWT_ALGORITHM))


def decode_access_token(token: str) -> dict[str, int | str]:
    """Decode and validate a JWT access token.

    :raises jose.ExpiredSignatureError: If the token has expired.
    :raises jose.JWTError: If the signature is invalid or token is malformed.
    """
    config = get_config()
    return jwt.decode(token, config.jwt_secret, algorithms=[_JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# In-memory brute-force protection (LAN-only, single-process)
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 15 * 60  # 15 minutes


class _RateLimitEntry:
    def __init__(self) -> None:
        self.failed_attempts = 0
        self.locked_until: float | None = None


_rate_limit_store: dict[str, _RateLimitEntry] = {}


def _now() -> float:
    return datetime.now(UTC).timestamp()


def _get_entry(ip: str) -> _RateLimitEntry:
    if ip not in _rate_limit_store:
        _rate_limit_store[ip] = _RateLimitEntry()
    return _rate_limit_store[ip]


def is_ip_locked(ip: str) -> tuple[bool, int]:
    """Check if *ip* is currently rate-limited.

    Returns (locked, seconds_remaining).
    """
    entry = _get_entry(ip)
    if entry.locked_until is None:
        return False, 0
    remaining = int(entry.locked_until - _now())
    if remaining <= 0:
        entry.locked_until = None
        return False, 0
    return True, remaining


def record_failed_attempt(ip: str) -> tuple[bool, int]:
    """Record a failed login attempt for *ip*.

    Returns (locked, seconds_remaining).
    """
    entry = _get_entry(ip)
    locked, remaining = is_ip_locked(ip)
    if locked:
        return True, remaining

    entry.failed_attempts += 1
    if entry.failed_attempts >= _MAX_ATTEMPTS:
        entry.locked_until = _now() + _LOCKOUT_SECONDS
        return True, _LOCKOUT_SECONDS
    return False, 0


def reset_failed_attempts(ip: str) -> None:
    """Clear failed attempts and lockout for *ip* (called on successful login)."""
    if ip in _rate_limit_store:
        del _rate_limit_store[ip]


# ---------------------------------------------------------------------------
# FastAPI auth dependencies
# ---------------------------------------------------------------------------

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=401,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_staff(token: str, db: AsyncSession) -> Staff:
    """Decode *token*, validate token_version, and return the Staff row."""
    try:
        payload = decode_access_token(token)
    except Exception:
        raise _CREDENTIALS_EXCEPTION from None

    staff_id = payload.get("sub")
    if not isinstance(staff_id, str):
        raise _CREDENTIALS_EXCEPTION

    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff: Staff | None = result.scalars().first()

    if staff is None or not staff.is_active:
        raise _CREDENTIALS_EXCEPTION

    jwt_version = payload.get("token_version")
    if not isinstance(jwt_version, int) or jwt_version != staff.token_version:
        raise _CREDENTIALS_EXCEPTION

    return staff


async def require_admin(staff: Staff) -> Staff:
    if staff.role != StaffRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return staff


async def require_cashier(staff: Staff) -> Staff:
    if staff.role not in (StaffRole.ADMIN, StaffRole.CASHIER):
        raise HTTPException(status_code=403, detail="Cashier or Admin access required")
    return staff
