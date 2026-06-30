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
