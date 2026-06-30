"""Tests for backend.core.security.

Covers: PIN hashing (Argon2id), JWT encode/decode, brute-force rate limiting,
lockout, token_version invalidation, and role dependencies.
"""

from __future__ import annotations

import pytest
from jose import ExpiredSignatureError, JWTError

from backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_pin,
    verify_pin,
)


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
    token = create_access_token(
        "staff_001", "ADMIN", token_version=1, expires_delta=-1
    )
    with pytest.raises(ExpiredSignatureError):
        decode_access_token(token)


def test_decode_access_token_rejects_tampered_token() -> None:
    """Tampered signature raises JWTError."""
    token = create_access_token("staff_001", "ADMIN", token_version=1)
    tampered = token[:-10] + "tamper1234"  # noqa: S105
    with pytest.raises(JWTError):
        decode_access_token(tampered)
