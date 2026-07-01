"""Arcade offline licensing subsystem."""

from backend.licensing.fingerprint import get_hardware_id
from backend.licensing.public_key import ARCADE_PUBLIC_KEY_HEX

__all__ = ["get_hardware_id", "ARCADE_PUBLIC_KEY_HEX"]
