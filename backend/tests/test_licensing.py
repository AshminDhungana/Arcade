"""Tests for backend.licensing.verify.

Scenarios (SDD Section 16.6):
  1. Valid perpetual license → ok, payload returned
  2. File missing → MISSING
  3. Payload tampered after signing → INVALID_SIGNATURE
  4. Signed with key A, verified against key B → INVALID_SIGNATURE
  5. Signature replaced with random bytes → INVALID_SIGNATURE
  6. Hardware ID mismatch → HARDWARE_MISMATCH
  7. TRIAL expired → TRIAL_EXPIRED
  8. TRIAL still valid → ok, payload returned
  9. Malformed (non-base64) file → INVALID_SIGNATURE
  10. All LicenseError messages are non-empty strings

FR-LIC-007 & FR-LIC-008 coverage.
"""

from __future__ import annotations

import base64
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from nacl.signing import SigningKey

from backend.licensing.verify import LicenseError, check_license

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_license(
    license_path: str, payload: dict[str, Any], signature: bytes
) -> None:
    envelope = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode(),
    }
    blob = base64.b64encode(json.dumps(envelope).encode()).decode()
    Path(license_path).write_text(blob)


def _make_license(
    private_key_hex: str,
    license_path: str,
    hardware_id: str,
    cafe_name: str = "Test Cafe",
    license_type: str = "PERPETUAL",
    trial_expires_at: str | None = None,
    tamper_after_sign: bool = False,
    bad_signature: bytes | None = None,
) -> None:
    payload = {
        "cafe_name": cafe_name,
        "hardware_id": hardware_id,
        "license_type": license_type,
        "issue_date": date.today().isoformat(),
        "trial_expires_at": trial_expires_at,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signing_key = SigningKey(bytes.fromhex(private_key_hex))
    signature = signing_key.sign(canonical).signature

    if tamper_after_sign:
        payload["cafe_name"] = "TAMPERED" + str(payload["cafe_name"])

    if bad_signature is not None:
        signature = bad_signature

    _write_license(license_path, payload, signature)


# ---------------------------------------------------------------------------
# Case 1: valid perpetual license
# ---------------------------------------------------------------------------


def test_valid_perpetual_license(tmp_path: Path) -> None:
    """A correctly signed, matching license is accepted."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()

    license_path = str(tmp_path / "license.key")
    hardware_id = "a" * 32
    _make_license(private_hex, license_path, hardware_id, cafe_name="Galaxy Cafe")

    import backend.licensing.verify as _verify_module

    original_get_hwid = _verify_module.get_hardware_id
    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    try:
        _verify_module.get_hardware_id = lambda: hardware_id
        _verify_module.ARCADE_PUBLIC_KEY_HEX = public_hex
        result = check_license(license_path)
    finally:
        _verify_module.get_hardware_id = original_get_hwid
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey

    assert result.ok is True
    assert result.error is None
    assert result.payload is not None
    assert result.payload["cafe_name"] == "Galaxy Cafe"
    assert result.payload["hardware_id"] == hardware_id
    assert result.payload["license_type"] == "PERPETUAL"


# ---------------------------------------------------------------------------
# Case 2: missing file
# ---------------------------------------------------------------------------


def test_missing_license_file(tmp_path: Path) -> None:
    """Non-existent license file -> MISSING error."""
    result = check_license(str(tmp_path / "nonexistent.key"))
    assert result.ok is False
    assert result.error is LicenseError.MISSING
    assert result.payload is None


# ---------------------------------------------------------------------------
# Case 3-5: invalid signature variants
# ---------------------------------------------------------------------------


def test_tampered_payload_invalid_signature(tmp_path: Path) -> None:
    """Mutating payload after signing breaks signature."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()

    license_path = str(tmp_path / "license.key")
    _make_license(private_hex, license_path, "a" * 32, tamper_after_sign=True)

    import backend.licensing.verify as _verify_module

    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    try:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = public_hex
        result = check_license(license_path)
    finally:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


def test_wrong_public_key_rejection(tmp_path: Path) -> None:
    """License signed with key A, verified with key B -> INVALID_SIGNATURE."""
    key_a = SigningKey.generate()
    key_b = SigningKey.generate()

    private_a = key_a.encode().hex()
    public_b = key_b.verify_key.encode().hex()

    license_path = str(tmp_path / "license.key")
    _make_license(private_a, license_path, "a" * 32)

    import backend.licensing.verify as _verify_module

    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    try:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = public_b
        result = check_license(license_path)
    finally:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


def test_corrupted_signature(tmp_path: Path) -> None:
    """Replacing signature with random bytes -> INVALID_SIGNATURE."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()

    license_path = str(tmp_path / "license.key")
    bad_sig = b"\x00" * 64
    _make_license(private_hex, license_path, "a" * 32, bad_signature=bad_sig)

    import backend.licensing.verify as _verify_module

    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    try:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = public_hex
        result = check_license(license_path)
    finally:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


# ---------------------------------------------------------------------------
# Case 6: hardware mismatch
# ---------------------------------------------------------------------------


def test_hardware_mismatch(tmp_path: Path) -> None:
    """License bound to hwid-A, verified on hwid-B -> HARDWARE_MISMATCH."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()

    license_path = str(tmp_path / "license.key")
    _make_license(private_hex, license_path, "a" * 32)

    import backend.licensing.verify as _verify_module

    original_get_hwid = _verify_module.get_hardware_id
    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    try:
        _verify_module.get_hardware_id = lambda: "b" * 32
        _verify_module.ARCADE_PUBLIC_KEY_HEX = public_hex
        result = check_license(license_path)
    finally:
        _verify_module.get_hardware_id = original_get_hwid
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey

    assert result.ok is False
    assert result.error is LicenseError.HARDWARE_MISMATCH


# ---------------------------------------------------------------------------
# Case 7-8: TRIAL expiry
# ---------------------------------------------------------------------------


def test_trial_expired(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TRIAL license with past expiry date -> TRIAL_EXPIRED."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()

    license_path = str(tmp_path / "license.key")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _make_license(
        private_hex,
        license_path,
        "a" * 32,
        license_type="TRIAL",
        trial_expires_at=yesterday,
    )

    monkeypatch.setenv("ARCADE_TEST_HWID", "a" * 32)

    import backend.licensing.verify as _verify_module

    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    try:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = public_hex
        result = check_license(license_path)
    finally:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey

    assert result.ok is False
    assert result.error is LicenseError.TRIAL_EXPIRED


def test_trial_still_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TRIAL license with future expiry date -> ok."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()

    license_path = str(tmp_path / "license.key")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    _make_license(
        private_hex,
        license_path,
        "a" * 32,
        license_type="TRIAL",
        trial_expires_at=tomorrow,
    )

    monkeypatch.setenv("ARCADE_TEST_HWID", "a" * 32)

    import backend.licensing.verify as _verify_module

    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    try:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = public_hex
        result = check_license(license_path)
    finally:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey

    assert result.ok is True
    assert result.error is None
    assert result.payload is not None
    assert result.payload["license_type"] == "TRIAL"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_malformed_envelope(tmp_path: Path) -> None:
    """A file that is not a valid base64 envelope -> INVALID_SIGNATURE."""
    license_path = tmp_path / "license.key"
    license_path.write_text("not a valid license")
    result = check_license(str(license_path))
    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


def test_all_license_error_messages() -> None:
    """Every LicenseError member has a non-empty string value."""
    for err in LicenseError:
        assert isinstance(err.value, str)
        assert err.value.strip() != ""
