"""Configuration loader for arcade.config.json.

This module provides the runtime configuration for the Arcade server.
Settings are loaded from ``arcade.config.json`` (produced by the setup wizard)
into an immutable Pydantic model using Pydantic v2.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Nested models for structured configuration values
# ---------------------------------------------------------------------------


class TuyaDeviceConfig(BaseModel):
    """Smart-plug entry for a console seat."""

    seat_id: str
    device_id: str
    local_key: str
    ip_address: str
    protocol_version: str = "3.3"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class Settings(BaseModel):
    """Runtime configuration model.

    Matches the ``arcade.config.json`` schema defined in the SDD §14.1
    (Appendix B). The wizard writes this file once; FastAPI reads it at
    startup via :func:`load_config`.
    """

    # ── Server basics ────────────────────────────────────────────────
    cafe_name: str = "Arcade"
    # Minutes remaining at which the low-time warning fires (Epic 5.5).
    # Defaults to 5; overridable via the LOW_TIME_WARNING_MINUTES env var so
    # ops can tune it without editing arcade.config.json. JSON, when present,
    # still takes precedence over the env fallback.
    low_time_warning_minutes: int = Field(
        default_factory=lambda: int(os.environ.get("LOW_TIME_WARNING_MINUTES", "5"))
    )
    host: str = "0.0.0.0"  # noqa: S104  # nosec B104
    # Default matches launcher.py DEFAULT_PORT (0.0.0.0:8741). The setup wizard
    # always writes an explicit port into arcade.config.json, so this is only a
    # fallback for pre-setup tooling that builds Settings() directly.
    port: int = Field(default=8741, ge=1, le=65535)

    # ──Database / Storage ────────────────────────────────────────────
    db_path: str = "./arcade.db"
    backup_dir: str = "./backups"
    backup_retain_days: int = Field(default=30, ge=1)
    backup_time: str = "03:00"

    # ── Staff accounts (hashed at rest) ──────────────────────────────
    admin_staff_id: str | None = None
    admin_pin_hash: str | None = None
    cashier_staff_id: str | None = None
    cashier_pin_hash: str | None = None
    override_code_hash: str | None = None

    # ── Security ──────────────────────────────────────────────────────
    jwt_secret: str = Field(  # noqa: S105 — not a hardcoded secret
        default="",
        min_length=64,
        description="Random 256-bit hex secret (64 hex chars).",
    )

    # ── Agent authentication (seat_id -> secret) ─────────────────────
    agent_secrets: dict[str, str] = Field(default_factory=dict)

    # ── Peripherals ──────────────────────────────────────────────────
    tuya_devices: list[TuyaDeviceConfig] = Field(default_factory=list)
    printer_type: Literal["usb", "network"] | None = "usb"
    printer_usb_vendor: str | None = None
    printer_usb_product: str | None = None

    # ── Validation helpers ────────────────────────────────────────────
    @field_validator("backup_time", mode="after")
    @classmethod
    def _validate_backup_time(cls, value: str) -> str:  # noqa: N805
        if not re.fullmatch(r"^([01]\d|2[0-3]):([0-5]\d)$", value):
            msg = f"backup_time must be HH:MM (24-hour), got: {value!r}"
            raise ValueError(msg)
        return value

    # ----------------------------------------------------------------
    # Convenience properties
    # ----------------------------------------------------------------
    @property
    def database_url(self) -> str:
        """Return SQLAlchemy async SQLite URL for aiosqlite."""
        return f"sqlite+aiosqlite:///{self.db_path}"


# ---------------------------------------------------------------------------
# Loader / singleton
# ---------------------------------------------------------------------------


def load_config(path: str = "arcade.config.json") -> Settings:
    """Read ``arcade.config.json`` and return a validated :class:`Settings`.

    :param path: Path to the configuration JSON file.
    :returns: Validated settings instance.
    :raises RuntimeError: If the file is missing or contains invalid JSON.
    :raises ValidationError: If the JSON does not match the schema.
    """
    config_file = Path(path)

    # Resolve relative paths from the project root (the directory
    # that contains ``backend/``). This ensures the config is found
    # regardless of the current working directory (e.g. when running
    # pytest from inside ``backend/`` or starting uvicorn there).
    if not config_file.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent
        config_file = project_root / path

    if not config_file.exists():
        msg = (
            f"arcade.config.json not found at {config_file}. "
            "Run the setup wizard (launcher.py)."
        )
        raise RuntimeError(msg)

    try:
        raw = config_file.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in arcade.config.json: {exc}"
        raise RuntimeError(msg) from exc

    return Settings.model_validate(data)


@lru_cache(maxsize=1)
def _cached_load_config(path: str = "arcade.config.json") -> Settings:
    return load_config(path)


def get_config() -> Settings:
    """Return the globally-cached configuration singleton.

    The first call reads the file from disk; subsequent calls return the
    same :class:`Settings` instance.
    """
    return _cached_load_config()
