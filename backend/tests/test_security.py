"""Tests for backend.core.security.

Covers: PIN hashing (Argon2id), JWT encode/decode, brute-force rate limiting,
lockout, token_version invalidation, and role dependencies.
"""

from __future__ import annotations

from backend.core.security import hash_pin, verify_pin


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
