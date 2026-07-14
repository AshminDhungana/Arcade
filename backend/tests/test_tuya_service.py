"""Tests for :mod:`backend.services.tuya_service`."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import tinytuya

from backend.core.config import Settings, TuyaDeviceConfig
from backend.services import tuya_service

DEVICE = TuyaDeviceConfig(
    seat_id="seat-1",
    device_id="dev-1",
    local_key="key-1",
    ip_address="192.168.1.50",
)

CFG_WITH_DEVICE = Settings(jwt_secret="a" * 64, tuya_devices=[DEVICE])
CFG_EMPTY = Settings(jwt_secret="a" * 64, tuya_devices=[])

DB = AsyncMock()


class _FakeDevice:
    """Mimics tinytuya.Device; records constructor args and toggle calls."""

    instances: list[_FakeDevice] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs
        self.turn_on_called = False
        self.turn_off_called = False
        _FakeDevice.instances.append(self)

    def turn_on(self) -> None:
        self.turn_on_called = True

    def turn_off(self) -> None:
        self.turn_off_called = True


class _BoomingDevice(_FakeDevice):
    """A device whose turn_on always raises (simulates a plug outage)."""

    def turn_on(self) -> None:
        raise RuntimeError("plug unreachable")


@pytest.fixture(autouse=True)
def reset() -> None:
    _FakeDevice.instances.clear()
    yield


@pytest.fixture
def patches(monkeypatch):
    monkeypatch.setattr(tinytuya, "Device", _FakeDevice)
    audit = AsyncMock()
    monkeypatch.setattr("backend.services.audit_service.log", audit)
    yield audit


async def test_power_on_skips_when_no_devices(patches, monkeypatch) -> None:
    """No tuya_devices => no device built, no audit."""
    monkeypatch.setattr(tuya_service, "get_flag", lambda _: True)
    monkeypatch.setattr(tuya_service, "get_config", lambda: CFG_EMPTY)
    await tuya_service.power_on(DB, "seat-1")
    assert _FakeDevice.instances == []
    patches.assert_not_awaited()


async def test_power_on_builds_device_and_turns_on(patches, monkeypatch) -> None:
    """With a configured device, turn_on is called and the action is audited."""
    monkeypatch.setattr(tuya_service, "get_flag", lambda _: True)
    monkeypatch.setattr(tuya_service, "get_config", lambda: CFG_WITH_DEVICE)
    await tuya_service.power_on(DB, "seat-1")
    assert len(_FakeDevice.instances) == 1
    device = _FakeDevice.instances[0]
    assert device.turn_on_called is True
    assert device.args == (DEVICE.device_id, DEVICE.ip_address, DEVICE.local_key)
    assert device.kwargs == {"version": DEVICE.protocol_version}
    patches.assert_awaited_once()


async def test_power_off_turns_off(patches, monkeypatch) -> None:
    """power_off drives turn_off and audits TUYA_POWER_OFF."""
    monkeypatch.setattr(tuya_service, "get_flag", lambda _: True)
    monkeypatch.setattr(tuya_service, "get_config", lambda: CFG_WITH_DEVICE)
    await tuya_service.power_off(DB, "seat-1")
    assert _FakeDevice.instances[0].turn_off_called is True
    patches.assert_awaited_once()


async def test_power_on_skips_when_flag_off(patches, monkeypatch) -> None:
    """Flag off => silent no-op."""
    monkeypatch.setattr(tuya_service, "get_flag", lambda _: False)
    monkeypatch.setattr(tuya_service, "get_config", lambda: CFG_WITH_DEVICE)
    await tuya_service.power_on(DB, "seat-1")
    assert _FakeDevice.instances == []
    patches.assert_not_awaited()


async def test_power_on_skips_when_no_device_for_seat(patches, monkeypatch) -> None:
    """seat_id has no Tuya config => silent no-op."""
    monkeypatch.setattr(tuya_service, "get_flag", lambda _: True)
    monkeypatch.setattr(tuya_service, "get_config", lambda: CFG_WITH_DEVICE)
    await tuya_service.power_on(DB, "seat-unknown")
    assert _FakeDevice.instances == []
    patches.assert_not_awaited()


async def test_power_on_failure_is_logged_not_raised(patches, monkeypatch) -> None:
    """A plug exception is swallowed; the call still returns normally."""
    monkeypatch.setattr(tinytuya, "Device", _BoomingDevice)
    monkeypatch.setattr(tuya_service, "get_flag", lambda _: True)
    monkeypatch.setattr(tuya_service, "get_config", lambda: CFG_WITH_DEVICE)
    # Must NOT raise.
    await tuya_service.power_on(DB, "seat-1")
    patches.assert_not_awaited()
