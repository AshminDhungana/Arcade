"""Display-free helpers for the Arcade license GUI.

Kept free of any Tkinter import so they are unit-testable without a display.
"""

from __future__ import annotations

from pathlib import Path

ICON_DIR = Path(__file__).resolve().parent / "icon"
LOGO_64 = ICON_DIR / "arcade_logo_64.png"


def resolve_logo_path() -> Path | None:
    """Return the committed 64px logo PNG, or None if it is missing."""
    return LOGO_64 if LOGO_64.exists() else None


def validate_inputs(
    hardware_id: str,
    cafe_name: str,
    license_type: str,
    trial_days: str | int | None,
) -> dict[str, str]:
    """Validate the license form. Returns {field: message} for invalid fields.

    Empty dict means the input is valid. ``trial_days`` is only checked for
    TRIAL licenses; PERPETUAL ignores it entirely.
    """
    errors: dict[str, str] = {}

    if not hardware_id or not hardware_id.strip():
        errors["hardware_id"] = "Hardware ID is required."
    if not cafe_name or not cafe_name.strip():
        errors["cafe_name"] = "Cafe Name is required."

    if license_type == "TRIAL":
        try:
            days = int(trial_days)
        except (TypeError, ValueError):
            errors["trial_days"] = "Trial Days must be a positive number."
        else:
            if days <= 0:
                errors["trial_days"] = "Trial Days must be a positive number."

    return errors
