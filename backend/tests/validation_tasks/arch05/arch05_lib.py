"""ARCH-05 spike library — minimal reimplementation of SDD §16.3-16.6.

NOT backend/licensing/*. Lifted verbatim into Phase 1 once validated.
All functions are synchronous (the licensing flow has no I/O that benefits
from async).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

import machineid  # py-machineid
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError


# ---------------------------------------------------------------------------
# 16.3 Hardware fingerprinting
# ---------------------------------------------------------------------------

def get_hardware_id() -> str:
    """Return a stable 32-hex Hardware ID.

    Primary source: py-machineid (no admin, cross-platform). SHA-256 fallback
    chain (SDD §16.3) is only used if py-machineid returns empty; on the
    validated OS (Windows) the primary path is taken.

    Test injection: if env var ARCADE_TEST_HWID is set, it is returned verbatim
    so tests can simulate a "different machine" deterministically.
    """
    override = os.environ.get("ARCADE_TEST_HWID")
    if override:
        return override

    machine_id = machineid.id()  # py-machineid's public API is .id()
    if machine_id:
        raw = f"py-machineid:{machine_id}"
    else:
        # Fallback: hash whatever identifiers we can gather. The spike only
        # needs a deterministic non-empty value here; full per-OS command set is
        # Phase 1 (validated OS is Windows, where the primary path is taken).
        import platform
        import uuid
        fallback_parts = [platform.node(), str(uuid.getnode())]
        raw = "|".join(p for p in fallback_parts if p)

    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# 16.6 Result types
# ---------------------------------------------------------------------------

class LicenseError(Enum):
    MISSING = "no license.key found"
    INVALID_SIGNATURE = "signature verification failed"
    HARDWARE_MISMATCH = "license is bound to a different machine"
    TRIAL_EXPIRED = "trial period has ended"


@dataclass
class LicenseResult:
    ok: bool
    error: Optional[LicenseError] = None
    payload: Optional[dict] = None


# ---------------------------------------------------------------------------
# 16.5 Keygen (internal only)
# ---------------------------------------------------------------------------

def generate_keypair() -> tuple[str, str]:
    """Generate a fresh Ed25519 keypair. Returns (private_key_hex, public_key_hex)."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()
    return private_hex, public_hex


def generate_license(
    private_key_hex: str,
    hardware_id: str,
    cafe_name: str,
    license_type: str = "PERPETUAL",
    trial_days: Optional[int] = None,
    issue_date: Optional[str] = None,
) -> str:
    """Sign and envelope a license payload. Returns base64-encoded license string.

    Payload + signature scheme per SDD §16.4/16.5: signature is over canonical
    (sorted-key, no-whitespace) JSON of the payload; the whole thing is wrapped
    as base64(json({payload, signature})) for transport.
    """
    if issue_date is None:
        issue_date = date.today().isoformat()
    trial_expires_at = None
    if license_type == "TRIAL" and trial_days is not None:
        trial_expires_at = (date.today() + timedelta(days=trial_days)).isoformat()

    payload = {
        "cafe_name": cafe_name,
        "hardware_id": hardware_id,
        "license_type": license_type,
        "issue_date": issue_date,
        "trial_expires_at": trial_expires_at,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signing_key = SigningKey(bytes.fromhex(private_key_hex))
    signature = signing_key.sign(canonical).signature

    envelope = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode(),
    }
    return base64.b64encode(json.dumps(envelope).encode()).decode()


# ---------------------------------------------------------------------------
# 16.6 Verification flow
# ---------------------------------------------------------------------------

def check_license(
    license_path: str,
    public_key_hex: str,
    hardware_id: Optional[str] = None,
) -> LicenseResult:
    """Verify a license.key file. Returns a LicenseResult (never raises on
    license failures; only on corrupt/unparseable files).

    hardware_id defaults to get_hardware_id(); passing it explicitly is how the
    foreign-machine rejection case is driven in tests.
    """
    if not os.path.exists(license_path):
        return LicenseResult(ok=False, error=LicenseError.MISSING)

    try:
        raw = base64.b64decode(open(license_path, "rb").read())
        parsed = json.loads(raw)
        payload = parsed["payload"]
        signature = base64.b64decode(parsed["signature"])
    except (ValueError, KeyError, json.JSONDecodeError):
        # Malformed envelope = not a valid license file.
        return LicenseResult(ok=False, error=LicenseError.INVALID_SIGNATURE)

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    try:
        VerifyKey(bytes.fromhex(public_key_hex)).verify(canonical, signature)
    except BadSignatureError:
        return LicenseResult(ok=False, error=LicenseError.INVALID_SIGNATURE)

    if hardware_id is None:
        hardware_id = get_hardware_id()
    if payload["hardware_id"] != hardware_id:
        return LicenseResult(ok=False, error=LicenseError.HARDWARE_MISMATCH)

    if payload["license_type"] == "TRIAL":
        trial_expires_at = payload.get("trial_expires_at")
        if trial_expires_at and date.today() > date.fromisoformat(trial_expires_at):
            return LicenseResult(ok=False, error=LicenseError.TRIAL_EXPIRED)

    return LicenseResult(ok=True, payload=payload)
