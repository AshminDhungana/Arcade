"""Offline Ed25519 license verification for Arcade.

Implements SDD Section 16.6: reads a signed license.key, verifies the Ed25519
signature against the embedded public key, checks hardware ID binding, and
validates trial expiry. Called by the Launcher before every start.

All functions are synchronous. `check_license()` never raises on license
failures — it returns a :class:`LicenseResult` for predictable error handling.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from backend.licensing.fingerprint import get_hardware_id
from backend.licensing.public_key import ARCADE_PUBLIC_KEY_HEX

__all__ = [
    "LicenseError",
    "LicenseResult",
    "check_license",
    "get_hardware_id",
    "ARCADE_PUBLIC_KEY_HEX",
]

# ---------------------------------------------------------------------------
# 16.6 Result types
# ---------------------------------------------------------------------------


class LicenseError(Enum):
    """Enumeration of the four possible license-failure reasons."""

    MISSING = "no license.key found"
    INVALID_SIGNATURE = "signature verification failed"
    HARDWARE_MISMATCH = "license is bound to a different machine"
    TRIAL_EXPIRED = "trial period has ended"


@dataclass
class LicenseResult:
    """Result of a license check.

    Attributes:
        ok: True when the license is valid and bound to this machine.
        error: One of :class:`LicenseError` variants when ``ok`` is False;
            None when ``ok`` is True.
        payload: The decoded, verified license payload when ``ok`` is True;
            None when ``ok`` is False.
    """

    ok: bool
    error: LicenseError | None = None
    payload: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Verification flow
# ---------------------------------------------------------------------------


def check_license(license_path: str = "license.key") -> LicenseResult:
    """Verify a license.key file.

    Steps (FR-LIC-007):
      1. Check file exists.
      2. Decode the base64 envelope.
      3. Verify the Ed25519 signature against the embedded public key.
      4. Compare the hardware_id in the payload to this machine.
      5. If TRIAL, check trial_expires_at against today.

    Args:
        license_path: Path to the license file (default: ``license.key``).

    Returns:
        :class:`LicenseResult` — never raises on license failures.
    """
    # 1. File exists?
    if not os.path.exists(license_path):
        return LicenseResult(ok=False, error=LicenseError.MISSING)

    # 2. Decode envelope
    try:
        raw = base64.b64decode(open(license_path, "rb").read())
        parsed = json.loads(raw)
        payload = parsed["payload"]
        signature = base64.b64decode(parsed["signature"])
    except (ValueError, KeyError, json.JSONDecodeError):
        # Malformed envelope = not a valid license file
        return LicenseResult(ok=False, error=LicenseError.INVALID_SIGNATURE)

    # 3. Verify Ed25519 signature
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    try:
        VerifyKey(bytes.fromhex(ARCADE_PUBLIC_KEY_HEX)).verify(canonical, signature)
    except BadSignatureError:
        return LicenseResult(ok=False, error=LicenseError.INVALID_SIGNATURE)

    # 4. Hardware ID match
    if payload["hardware_id"] != get_hardware_id():
        return LicenseResult(ok=False, error=LicenseError.HARDWARE_MISMATCH)

    # 5. Trial expiry check
    if payload["license_type"] == "TRIAL":
        trial_expires_at = payload.get("trial_expires_at")
        if trial_expires_at and date.today() > date.fromisoformat(trial_expires_at):
            return LicenseResult(ok=False, error=LicenseError.TRIAL_EXPIRED)

    return LicenseResult(ok=True, payload=payload)
