"""TuyaService — local-LAN smart-plug control for console power.

Business logic for powering a seat's console on/off via the TinyTuya local
protocol (NO cloud at runtime — CLAUDE.md constraint). Feature-gated via the
``enable_tuya`` flag and config-driven via ``Settings.tuya_devices``.

All hardware I/O is wrapped in :func:`asyncio.to_thread` so a slow or
unreachable plug never blocks the calling session or checkout. Any failure is
logged at WARNING and swallowed — a plug outage must never abort a session
start or a checkout.
"""

from __future__ import annotations

import asyncio
import logging

import tinytuya
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings, TuyaDeviceConfig, get_config
from backend.core.feature_flags import get_flag
from backend.models._enums import AuditAction
from backend.services import audit_service

logger = logging.getLogger(__name__)

_TUYA_FLAG = "enable_tuya"


def _device_for_seat(settings: Settings, seat_id: str) -> TuyaDeviceConfig | None:
    """Return the Tuya device config bound to *seat_id*, or ``None``."""
    return next((d for d in settings.tuya_devices if d.seat_id == seat_id), None)


def _build_device(device_cfg: TuyaDeviceConfig) -> tinytuya.Device:
    """Construct a local-LAN TinyTuya device from config."""
    return tinytuya.Device(
        device_cfg.device_id,
        device_cfg.ip_address,
        device_cfg.local_key,
        version=device_cfg.protocol_version,
    )


async def power_on(db: AsyncSession, seat_id: str) -> None:
    """Power a seat's console ON (best-effort, non-blocking, non-fatal)."""
    if not get_flag(_TUYA_FLAG):
        return
    settings = get_config()
    if not settings.tuya_devices:
        return
    device_cfg = _device_for_seat(settings, seat_id)
    if device_cfg is None:
        return
    try:
        device = _build_device(device_cfg)
        await asyncio.to_thread(device.turn_on)
    except Exception:
        logger.warning("Tuya power-on failed for seat %s", seat_id, exc_info=True)
        return
    await audit_service.log(
        db,
        action=AuditAction.TUYA_POWER_ON,
        entity_type="seat",
        entity_id=seat_id,
        detail=f"device_id={device_cfg.device_id}",
    )


async def power_off(db: AsyncSession, seat_id: str) -> None:
    """Power a seat's console OFF (best-effort, non-blocking, non-fatal)."""
    if not get_flag(_TUYA_FLAG):
        return
    settings = get_config()
    if not settings.tuya_devices:
        return
    device_cfg = _device_for_seat(settings, seat_id)
    if device_cfg is None:
        return
    try:
        device = _build_device(device_cfg)
        await asyncio.to_thread(device.turn_off)
    except Exception:
        logger.warning("Tuya power-off failed for seat %s", seat_id, exc_info=True)
        return
    await audit_service.log(
        db,
        action=AuditAction.TUYA_POWER_OFF,
        entity_type="seat",
        entity_id=seat_id,
        detail=f"device_id={device_cfg.device_id}",
    )
