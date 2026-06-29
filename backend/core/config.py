"""Configuration loader for arcade.config.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration model."""

    cafe_name: str = "Arcade"
    host: str = ""
    port: int = 8000
    db_path: str = "./arcade.db"
    backup_dir: str = "./backups"
    backup_retain_days: int = 30
    backup_time: str = "03:00"
    admin_staff_id: str | None = None
    admin_pin_hash: str | None = None
    cashier_staff_id: str | None = None
    cashier_pin_hash: str | None = None
    jwt_secret: str = Field(default="", min_length=32)
    agent_secrets: dict[str, str] = Field(default_factory=dict)
    tuya_devices: list[dict[str, str]] = Field(default_factory=list)
    printer_type: str = "usb"


@lru_cache(maxsize=1)
def get_config(path: str = "arcade.config.json") -> Settings:
    config_file = Path(path)
    if not config_file.exists():
        raise RuntimeError(
            "arcade.config.json not found. Run the setup wizard (launcher.py)."
        )
    data = json.loads(config_file.read_text(encoding="utf-8"))
    return Settings.model_validate(data)
