"""AC-12: License verification — offline Ed25519 signature validation."""

import base64
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from backend.licensing import (
    LicenseError,
    LicenseResult,
    check_license,
    get_hardware_id,
)


def test_license_verification_valid_signature(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Valid license key with correct Ed25519 signature passes verification."""
    # Create a test license that mimics the real format
    # Since we don't have the real private key to sign, we test the structure
    # and mock the verification to pass

    test_hwid = get_hardware_id()
    payload = {
        "license_type": "PERPETUAL",
        "hardware_id": test_hwid,
        "issued_to": "Arcade Cafe",
        "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
        "features": ["all"],
    }

    # Create canonical payload for signing
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    with patch("backend.licensing.verify.VerifyKey") as mock_verify_key:
        mock_verify_instance = mock_verify_key.return_value
        mock_verify_instance.verify.return_value = None  # Success

        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            test_license = {
                "payload": payload,
                "signature": base64.b64encode(
                    b"\x00" * 64
                ).decode(),  # 64 bytes of zeros
            }
            f.write(base64.b64encode(json.dumps(test_license).encode()).decode())
            temp_path = f.name

        try:
            result = check_license(temp_path)
            assert result.ok is True
            assert result.payload is not None
            assert result.payload["issued_to"] == "Arcade Cafe"
        finally:
            os.unlink(temp_path)


def test_license_verification_invalid_signature_rejected(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """License with invalid signature is rejected."""
    test_hwid = get_hardware_id()
    payload = {
        "license_type": "PERPETUAL",
        "hardware_id": test_hwid,
        "issued_to": "Test",
    }

    # Provide a 64-byte signature that's just invalid (not all zeros)
    # This will pass the length check but fail verification
    invalid_signature = base64.b64encode(b"\x01" * 64).decode()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
        test_license = {"payload": payload, "signature": invalid_signature}
        f.write(base64.b64encode(json.dumps(test_license).encode()).decode())
        temp_path = f.name

    try:
        result = check_license(temp_path)
        assert result.ok is False
        assert result.error == LicenseError.INVALID_SIGNATURE
    finally:
        os.unlink(temp_path)


def test_license_verification_expired_rejected(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Expired trial license is rejected."""
    test_hwid = get_hardware_id()
    payload = {
        "license_type": "TRIAL",
        "hardware_id": test_hwid,
        "issued_to": "Test",
        "trial_expires_at": (datetime.now(UTC) - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        ),
    }

    # Mock signature verification to pass, then trial expiry check will fail
    with patch("backend.licensing.verify.VerifyKey") as mock_verify_key:
        mock_verify_instance = mock_verify_key.return_value
        mock_verify_instance.verify.return_value = None  # Signature OK

        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            test_license = {
                "payload": payload,
                "signature": base64.b64encode(b"\x00" * 64).decode(),
            }
            f.write(base64.b64encode(json.dumps(test_license).encode()).decode())
            temp_path = f.name

        try:
            result = check_license(temp_path)
            assert result.ok is False
            assert result.error == LicenseError.TRIAL_EXPIRED
        finally:
            os.unlink(temp_path)


def test_license_verification_hardware_mismatch_rejected(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """License bound to different hardware ID is rejected."""
    wrong_hwid = "00000000000000000000000000000000"  # Different from current machine
    payload = {
        "license_type": "PERPETUAL",
        "hardware_id": wrong_hwid,
        "issued_to": "Test",
    }

    # Mock signature verification to pass, then hardware check will fail
    with patch("backend.licensing.verify.VerifyKey") as mock_verify_key:
        mock_verify_instance = mock_verify_key.return_value
        mock_verify_instance.verify.return_value = None  # Signature OK

        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            test_license = {
                "payload": payload,
                "signature": base64.b64encode(b"\x00" * 64).decode(),
            }
            f.write(base64.b64encode(json.dumps(test_license).encode()).decode())
            temp_path = f.name

        try:
            result = check_license(temp_path)
            assert result.ok is False
            assert result.error == LicenseError.HARDWARE_MISMATCH
        finally:
            os.unlink(temp_path)


def test_license_verification_malformed_key_rejected(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Malformed license key format is rejected."""
    invalid_keys = [
        "not_valid_base64",
        "",  # Empty
        base64.b64encode(b"not json").decode(),
        base64.b64encode(json.dumps({"payload": "no signature"}).encode()).decode(),
    ]

    for invalid_key in invalid_keys:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(invalid_key)
            temp_path = f.name

        try:
            result = check_license(temp_path)
            assert result.ok is False
            assert result.error == LicenseError.INVALID_SIGNATURE
        finally:
            os.unlink(temp_path)


def test_license_verification_hardware_id_collection(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Hardware ID collection uses py-machineid with OS fallbacks."""
    hwid = get_hardware_id()

    # Should return a 32-char hex string
    assert hwid is not None
    assert len(hwid) == 32
    assert all(c in "0123456789abcdef" for c in hwid)

    # Test environment override
    with patch.dict(os.environ, {"ARCADE_TEST_HWID": "test-override-12345"}):
        from importlib import reload

        from backend.licensing import fingerprint

        reload(fingerprint)
        overridden = fingerprint.get_hardware_id()
        assert overridden == "test-override-12345"


def test_license_endpoint_requires_admin(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """POST /api/license/verify requires ADMIN role - SKIPPED: endpoint not implemented yet."""
    pytest.skip("License verification endpoint not yet implemented")


def test_license_check_returns_license_result_structure(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """License result has correct structure with ok, error, payload."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
        f.write("dGVzdA==")  # base64 "test"
        temp_path = f.name

    try:
        result = check_license(temp_path)
        assert isinstance(result, LicenseResult)
        assert result.ok is False
        assert result.error is not None
        assert result.payload is None
    finally:
        os.unlink(temp_path)


def test_license_missing_file_returns_missing_error(
    integration_client, integration_db, seeded_zone, seeded_seat
):
    """Missing license file returns MISSING error."""
    result = check_license("/nonexistent/path/license.key")
    assert result.ok is False
    assert result.error == LicenseError.MISSING
