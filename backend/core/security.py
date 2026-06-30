"""Security utilities: PIN hashing, JWT, rate limiting, and FastAPI auth dependencies."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

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

from datetime import datetime, timedelta, timezone

from jose import jwt

from backend.core.config import get_config

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
        "exp": (datetime.now(timezone.utc) + delta).timestamp(),
    }
    return str(jwt.encode(payload, config.jwt_secret, algorithm=_JWT_ALGORITHM))


def decode_access_token(token: str) -> dict[str, int | str]:
    """Decode and validate a JWT access token.

    :raises jose.ExpiredSignatureError: If the token has expired.
    :raises jose.JWTError: If the signature is invalid or token is malformed.
    """
    config = get_config()
    return jwt.decode(
        token, config.jwt_secret, algorithms=[_JWT_ALGORITHM]
    )  # type: ignore[no-any-return]