"""Tests for backend.core.config.

Scenarios:
1. load_config succeeds with a valid JSON file.
2. load_config raises RuntimeError when the file is missing.
3. load_config raises RuntimeError when the file contains invalid JSON.
4. Port > 65535 triggers a Pydantic ValidationError.
5. jwt_secret shorter than 64 chars triggers a ValidationError.
6. get_config returns the same singleton on repeated calls (cache hit).
7. Invalid backup_time format triggers a ValidationError.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from backend.core.config import get_config, load_config

# ---------------------------------------------------------------------------
# Fixture: minimal valid config payload
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_config() -> dict[str, Any]:
    return {
        "cafe_name": "Galaxy Gaming Lounge",
        "host": "192.168.1.100",
        "port": 8080,
        "db_path": "./arcade.db",
        "backup_dir": "./backups",
        "backup_retain_days": 14,
        "backup_time": "02:30",
        "admin_staff_id": "admin001",
        "admin_pin_hash": "$argon2id$...",
        "cashier_staff_id": "cash001",
        "cashier_pin_hash": "$argon2id$...",
        "override_code_hash": "$argon2id$...",
        "jwt_secret": "a" * 64,
        "agent_secrets": {"seat_001": "abc123"},
        "tuya_devices": [
            {
                "seat_id": "console_01",
                "device_id": "dev1",
                "local_key": "key1",
                "ip_address": "192.168.1.50",
                "protocol_version": "3.3",
            }
        ],
        "printer_type": "usb",
        "printer_usb_vendor": "0x04b8",
        "printer_usb_product": "0x0202",
    }


# ---------------------------------------------------------------------------
# Scenario 1: valid config loads successfully
# ---------------------------------------------------------------------------


def test_load_valid_config(tmp_path: Path, valid_config: dict[str, Any]) -> None:
    config_file = tmp_path / "arcade.config.json"
    config_file.write_text(json.dumps(valid_config), encoding="utf-8")

    settings = load_config(str(config_file))

    assert settings.cafe_name == "Galaxy Gaming Lounge"
    assert settings.host == "192.168.1.100"
    assert settings.port == 8080
    assert settings.backup_retain_days == 14
    assert settings.backup_time == "02:30"
    assert settings.override_code_hash is not None
    assert settings.agent_secrets == {"seat_001": "abc123"}
    assert len(settings.tuya_devices) == 1
    assert settings.tuya_devices[0].seat_id == "console_01"
    assert settings.printer_usb_vendor == "0x04b8"
    assert settings.database_url == "sqlite+aiosqlite:///./arcade.db"


# ---------------------------------------------------------------------------
# Scenario 2: missing file raises RuntimeError
# ---------------------------------------------------------------------------


def test_missing_file_raises_runtime_error(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.config.json"
    with pytest.raises(RuntimeError, match="not found"):
        load_config(str(missing))


# ---------------------------------------------------------------------------
# Scenario 3: invalid JSON raises RuntimeError
# ---------------------------------------------------------------------------


def test_invalid_json_raises_runtime_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.config.json"
    bad.write_text("not-json-{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Invalid JSON"):
        load_config(str(bad))


# ---------------------------------------------------------------------------
# Scenario 4: bad port range
# ---------------------------------------------------------------------------


def test_bad_port_range(tmp_path: Path) -> None:
    bad = tmp_path / "bad.config.json"
    bad.write_text(json.dumps({"port": 70000}), encoding="utf-8")
    with pytest.raises(ValidationError, match="port"):
        load_config(str(bad))


# ---------------------------------------------------------------------------
# Scenario 5: jwt_secret too short
# ---------------------------------------------------------------------------


def test_jwt_secret_too_short(tmp_path: Path, valid_config: dict[str, Any]) -> None:
    valid_config["jwt_secret"] = "short"
    bad = tmp_path / "bad.config.json"
    bad.write_text(json.dumps(valid_config), encoding="utf-8")
    with pytest.raises(ValidationError, match="jwt_secret"):
        load_config(str(bad))


# ---------------------------------------------------------------------------
# Scenario 6: singleton caching
# ---------------------------------------------------------------------------


def test_singleton_caching(
    tmp_path: Path,
    valid_config: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.core.config as config_module

    # Clear any previously-cached state
    config_module._cached_load_config.cache_clear()

    config_file = tmp_path / "arcade.config.json"
    config_file.write_text(json.dumps(valid_config), encoding="utf-8")

    # Point the default relative path at the temp directory
    monkeypatch.chdir(tmp_path)

    first = get_config()
    second = get_config()
    assert first is second


# ---------------------------------------------------------------------------
# Scenario 7: invalid backup_time format
# ---------------------------------------------------------------------------


def test_invalid_backup_time_format(
    tmp_path: Path, valid_config: dict[str, Any]
) -> None:
    valid_config["backup_time"] = "25:00"
    bad = tmp_path / "bad.config.json"
    bad.write_text(json.dumps(valid_config), encoding="utf-8")
    with pytest.raises(ValidationError, match="backup_time"):
        load_config(str(bad))


# ---------------------------------------------------------------------------
# Scenario 8: low_time_warning_minutes (Epic 5.5)
# ---------------------------------------------------------------------------


def test_low_time_warning_minutes_default() -> None:
    from backend.core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.low_time_warning_minutes == 5


def test_low_time_warning_minutes_env_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("LOW_TIME_WARNING_MINUTES", "10")
    from backend.core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.low_time_warning_minutes == 10
