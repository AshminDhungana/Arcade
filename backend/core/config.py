"""Configuration loader for arcade.config.json.

This module provides the runtime configuration for the Arcade server.
Settings are loaded from ``arcade.config.json`` (produced by the setup wizard)
into an immutable Pydantic model using Pydantic v2.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

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
    port: int = Field(default=8742, ge=1, le=65535)

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
    printer_uri: str | None = None

    # ── Validation helpers ────────────────────────────────────────────
    @field_validator("backup_time", mode="after")
    @classmethod
    def _validate_backup_time(cls, value: str) -> str:  # noqa: N805
        if not re.fullmatch(r"^([01]\d|2[0-3]):([0-5]\d)$", value):
            msg = f"backup_time must be HH:MM (24-hour), got: {value!r}"
            raise ValueError(msg)
        return value

    @field_validator("printer_uri", mode="after")
    @classmethod
    def _validate_printer_uri(cls, value: str | None) -> str | None:
        """Validate printer URI scheme is a supported printer protocol."""
        if value is None:
            return None
        valid_schemes = {"usb", "socket", "ipp", "http", "https", "lpd"}
        parsed = urlparse(value)
        if parsed.scheme.lower() not in valid_schemes:
            msg = (
                f"printer_uri scheme '{parsed.scheme}' not supported. "
                f"Valid schemes: {', '.join(sorted(valid_schemes))}"
            )
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

    # Resolve relative paths by checking multiple locations in priority order:
    # 1. Absolute path (as-is)
    # 2. PyInstaller bundle (sys._MEIPASS) - for bundled data files
    # 3. Executable directory (sys.executable parent) - for runtime-created
    #    config in onedir mode
    # 4. Current working directory - fallback for development and edge cases
    # 5. Project root (parent of backend/) - for source runs
    if not config_file.is_absolute():
        candidate_paths: list[Path] = []

        # 1. PyInstaller bundle (sys._MEIPASS)
        with contextlib.suppress(Exception):
            import sys

            if hasattr(sys, "_MEIPASS"):
                candidate_paths.append(Path(sys._MEIPASS) / path)

        # 2. Executable directory (for PyInstaller --onedir runtime config)
        with contextlib.suppress(Exception):
            import sys

            if getattr(sys, "frozen", False):
                exe_dir = Path(sys.executable).resolve().parent
                candidate_paths.append(exe_dir / path)

        # 3. Current working directory
        with contextlib.suppress(Exception):
            candidate_paths.append(Path.cwd() / path)

        # 4. Project root (parent of backend/) - for source runs
        with contextlib.suppress(Exception):
            project_root = Path(__file__).resolve().parent.parent.parent
            candidate_paths.append(project_root / path)

        # Use the first existing path
        for candidate in candidate_paths:
            if candidate.exists():
                config_file = candidate
                break
        else:
            # None found - use the first candidate for error message
            config_file = candidate_paths[0] if candidate_paths else Path(path)

    if not config_file.exists():
        msg = (
            f"arcade.config.json not found at {config_file}. "
            "Run the setup wizard (launcher.py)."
        )
        raise RuntimeError(msg)

    # Workaround for PyInstaller permission issues on Windows:
    # data files in _MEIPASS may have restricted permissions.
    # Try to read with fallback to copying to a temp location.
    try:
        raw = config_file.read_text(encoding="utf-8")
    except PermissionError:
        import shutil
        import tempfile

        try:
            # Try to make the file readable first
            os.chmod(config_file, 0o644)
            raw = config_file.read_text(encoding="utf-8")
        except (PermissionError, OSError):
            # Fallback: try os.open with explicit flags
            try:
                fd = os.open(config_file, os.O_RDONLY | os.O_BINARY)
                try:
                    raw = os.read(fd, os.path.getsize(config_file)).decode("utf-8")
                finally:
                    os.close(fd)
            except (PermissionError, OSError):
                # Last resort: try shutil.copy to a temp location
                tmp = Path(tempfile.gettempdir()) / f"arcade_config_{os.getpid()}.json"
                try:
                    shutil.copy2(config_file, tmp)
                    raw = tmp.read_text(encoding="utf-8")
                finally:
                    tmp.unlink(missing_ok=True)

    try:
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
