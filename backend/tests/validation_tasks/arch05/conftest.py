"""Shared fixtures for the ARCH-05 validation spike."""
from __future__ import annotations

import pytest

from arch05.arch05_lib import generate_keypair, generate_license


@pytest.fixture(scope="session")
def keypair() -> tuple[str, str]:
    """A single Ed25519 keypair shared across the whole session."""
    return generate_keypair()


@pytest.fixture
def foreign_keypair() -> tuple[str, str]:
    """A second, independent keypair for the 'wrong key' tamper case."""
    return generate_keypair()


@pytest.fixture
def tmp_license_factory(tmp_path):
    """Return a callable that writes a license.key to a clean tmp dir.

    Usage: path = tmp_license_factory(priv, hwid, cafe_name="X", ...)
    Each call writes to the same file (license.key) inside a fresh tmp_path.
    """
    def _make(
        private_key_hex: str,
        hardware_id: str,
        cafe_name: str = "Test Cafe",
        license_type: str = "PERPETUAL",
        trial_days: int | None = None,
    ):
        license_path = tmp_path / "license.key"
        blob = generate_license(
            private_key_hex,
            hardware_id,
            cafe_name,
            license_type=license_type,
            trial_days=trial_days,
        )
        license_path.write_text(blob)
        return str(license_path)

    return _make
