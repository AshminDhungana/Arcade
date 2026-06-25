"""ARCH-05 validation tests — SDD §16.6 outcomes + tamper cases.

Cases 1-5: round-trip, MISSING, and the three INVALID_SIGNATURE variants.
Cases 6-10 are added in Task 7.
"""
from __future__ import annotations

import base64
import json

from arch05.arch05_lib import LicenseError, check_license, generate_license, get_hardware_id


# ---------------------------------------------------------------------------
# Case 1: round-trip happy path
# ---------------------------------------------------------------------------

def test_round_trip_valid_license(keypair, tmp_license_factory):
    priv, pub = keypair
    hwid = get_hardware_id()
    path = tmp_license_factory(priv, hwid, cafe_name="Galaxy Gaming Lounge")

    result = check_license(path, pub)

    assert result.ok is True
    assert result.error is None
    assert result.payload["cafe_name"] == "Galaxy Gaming Lounge"
    assert result.payload["hardware_id"] == hwid
    assert result.payload["license_type"] == "PERPETUAL"


# ---------------------------------------------------------------------------
# Case 2: no license.key file
# ---------------------------------------------------------------------------

def test_missing_license_file(keypair, tmp_path):
    _, pub = keypair
    missing_path = str(tmp_path / "does_not_exist.key")

    result = check_license(missing_path, pub)

    assert result.ok is False
    assert result.error is LicenseError.MISSING


# ---------------------------------------------------------------------------
# Case 3: payload byte tampered after signing
# ---------------------------------------------------------------------------

def test_invalid_signature_payload_tampered(keypair, tmp_path):
    priv, pub = keypair
    hwid = get_hardware_id()

    # Build a valid license, then mutate one byte of the cafe_name in the
    # already-signed payload. The signature no longer matches.
    blob = generate_license(priv, hwid, cafe_name="Galaxy Gaming Lounge")
    envelope = json.loads(base64.b64decode(blob))
    envelope["payload"]["cafe_name"] = "Malaxy Gaming Lounge"  # G -> M
    tampered_blob = base64.b64encode(json.dumps(envelope).encode()).decode()

    path = tmp_path / "license.key"
    path.write_text(tampered_blob)

    result = check_license(str(path), pub)

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


# ---------------------------------------------------------------------------
# Case 4: signed with key A, verified with key B
# ---------------------------------------------------------------------------

def test_invalid_signature_wrong_key(keypair, foreign_keypair, tmp_license_factory):
    priv_a, _ = keypair          # signs the license
    _, pub_b = foreign_keypair   # tries to verify
    hwid = get_hardware_id()
    path = tmp_license_factory(priv_a, hwid)

    result = check_license(path, pub_b)

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


# ---------------------------------------------------------------------------
# Case 5: corrupted signature (random bytes)
# ---------------------------------------------------------------------------

def test_invalid_signature_corrupted(keypair, tmp_path):
    priv, pub = keypair
    hwid = get_hardware_id()

    blob = generate_license(priv, hwid, cafe_name="Test Cafe")
    envelope = json.loads(base64.b64decode(blob))
    # Replace the signature with 64 random-ish bytes (Ed25519 sig is 64 bytes).
    envelope["signature"] = base64.b64encode(b"\x00" * 64).decode()
    corrupted_blob = base64.b64encode(json.dumps(envelope).encode()).decode()

    path = tmp_path / "license.key"
    path.write_text(corrupted_blob)

    result = check_license(str(path), pub)

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE
