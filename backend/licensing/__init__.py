"""Arcade offline licensing subsystem.

Exports the public API for hardware fingerprinting and license verification.
"""

from backend.licensing.fingerprint import get_hardware_id
from backend.licensing.public_key import ARCADE_PUBLIC_KEY_HEX
from backend.licensing.verify import LicenseError, LicenseResult, check_license

__all__ = [
    "get_hardware_id",
    "ARCADE_PUBLIC_KEY_HEX",
    "check_license",
    "LicenseError",
    "LicenseResult",
]
