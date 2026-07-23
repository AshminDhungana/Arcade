"""Tests for printer_uri field in Settings model."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.core.config import Settings, load_config


@pytest.fixture
def valid_config() -> dict:
    return {
        "cafe_name": "Test Cafe",
        "host": "127.0.0.1",
        "port": 8000,
        "db_path": "./arcade.db",
        "backup_dir": "./backups",
        "backup_retain_days": 30,
        "backup_time": "03:00",
        "admin_staff_id": "admin1",
        "admin_pin_hash": "$argon2id$...",
        "cashier_staff_id": "cashier1",
        "cashier_pin_hash": "$argon2id$...",
        "override_code_hash": "$argon2id$...",
        "jwt_secret": "a" * 64,
        "agent_secrets": {"seat_001": "secret123"},
        "tuya_devices": [],
        "printer_type": "usb",
        "printer_usb_vendor": "0x04b8",
        "printer_usb_product": "0x0202",
    }


def test_printer_uri_field_exists_and_optional(valid_config: dict) -> None:
    """Settings model accepts optional printer_uri field."""
    valid_config["printer_uri"] = "usb://USB001"
    settings = Settings.model_validate(valid_config)
    assert settings.printer_uri == "usb://USB001"


def test_printer_uri_field_optional(valid_config: dict) -> None:
    """Settings model works without printer_uri field."""
    # Remove printer fields to test defaults
    settings = Settings.model_validate(valid_config)
    assert settings.printer_uri is None


def test_printer_uri_loads_from_config_file(tmp_path: Path, valid_config: dict) -> None:
    """load_config reads printer_uri from arcade.config.json."""
    valid_config["printer_uri"] = "socket://192.168.1.100:9100"
    config_file = tmp_path / "arcade.config.json"
    config_file.write_text(json.dumps(valid_config), encoding="utf-8")

    settings = load_config(str(config_file))
    assert settings.printer_uri == "socket://192.168.1.100:9100"


def test_printer_uri_accepts_usb_uri(valid_config: dict) -> None:
    """Accepts usb:// URIs."""
    valid_config["printer_uri"] = "usb://USB001"
    settings = Settings.model_validate(valid_config)
    assert settings.printer_uri == "usb://USB001"


def test_printer_uri_accepts_network_uris(valid_config: dict) -> None:
    """Accepts network printer URIs (socket, ipp, http, https, lpd)."""
    for uri in [
        "socket://192.168.1.50:9100",
        "ipp://192.168.1.50:631/ipp/print",
        "http://192.168.1.50:631/printers/printer1",
        "https://printer.example.com/ipp/print",
        "lpd://192.168.1.50/queue",
    ]:
        valid_config["printer_uri"] = uri
        settings = Settings.model_validate(valid_config)
        assert settings.printer_uri == uri


def test_printer_uri_rejects_invalid_scheme(valid_config: dict) -> None:
    """Rejects URIs with unknown schemes."""
    valid_config["printer_uri"] = "ftp://printer.example.com"
    with pytest.raises(ValidationError, match="printer_uri"):
        Settings.model_validate(valid_config)
