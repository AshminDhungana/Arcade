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


# ---------------------------------------------------------------------------
# Case 6: license bound to hwid-A, verified against hwid-B (foreign machine)
# This is the "verify on a different machine -> reject" criterion. Proven by
# injecting a foreign hardware ID rather than a second physical machine
# (single Windows machine available; macOS/Linux deferred).
# ---------------------------------------------------------------------------

def test_hardware_mismatch_rejects_foreign_machine(keypair, tmp_license_factory):
    priv, pub = keypair
    # License is bound to this real machine's hardware ID...
    real_hwid = get_hardware_id()
    path = tmp_license_factory(priv, real_hwid, cafe_name="Bound Machine")

    # ...but we verify as if we are a DIFFERENT machine by passing a foreign ID.
    foreign_hwid = "f" * 32  # 32-hex, guaranteed != real_hwid
    assert foreign_hwid != real_hwid

    result = check_license(path, pub, hardware_id=foreign_hwid)

    assert result.ok is False
    assert result.error is LicenseError.HARDWARE_MISMATCH


# ---------------------------------------------------------------------------
# Case 7: TRIAL expired (trial_expires_at = yesterday)
# ---------------------------------------------------------------------------

def test_trial_expired(keypair, tmp_license_factory):
    priv, pub = keypair
    hwid = get_hardware_id()
    # trial_days=-1 -> trial_expires_at = yesterday (timedelta handles negatives).
    path = tmp_license_factory(
        priv, hwid, cafe_name="Expired Trial", license_type="TRIAL", trial_days=-1
    )

    result = check_license(path, pub)

    assert result.ok is False
    assert result.error is LicenseError.TRIAL_EXPIRED


# ---------------------------------------------------------------------------
# Case 8: TRIAL still valid (trial_expires_at = tomorrow)
# ---------------------------------------------------------------------------

def test_trial_still_valid(keypair, tmp_license_factory):
    priv, pub = keypair
    hwid = get_hardware_id()
    path = tmp_license_factory(
        priv, hwid, cafe_name="Active Trial", license_type="TRIAL", trial_days=1
    )

    result = check_license(path, pub)

    assert result.ok is True
    assert result.error is None
    assert result.payload["license_type"] == "TRIAL"


# ---------------------------------------------------------------------------
# Case 9: hardware ID idempotent within a process (reboot-stability proxy)
# ---------------------------------------------------------------------------

def test_hardware_id_is_stable_within_process():
    """Within a single process, get_hardware_id() must return the same value.

    True cross-reboot stability is an OS-level property the spike cannot prove
    without a reboot; this asserts the in-process precondition and the report
    lists 'reboot + re-run' as a manual checklist item.
    """
    first = get_hardware_id()
    second = get_hardware_id()

    assert first == second
    assert len(first) == 32  # 32-hex per SDD §16.3


# ---------------------------------------------------------------------------
# Case 10: py-machineid returns non-empty with no admin elevation
# ---------------------------------------------------------------------------

def test_machineid_returns_value_without_admin():
    """The suite itself runs unelevated; this additionally asserts machineid.id()
    returns a non-empty value (proving the no-admin primary path works)."""
    import machineid

    value = machineid.id()

    assert isinstance(value, str)
    assert value.strip() != ""
