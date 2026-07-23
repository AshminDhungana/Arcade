"""Arcade business logic services."""

from backend.services import (
    auth_service,
    backup_service,
    billing_service,
    device_type_service,
    inventory_service,
    package_service,
    peak_schedule_service,
    pos_service,
    printer_discovery,
    remote_command_service,
    reservation_service,
    seat_service,
    session_service,
    shift_service,
    staff_zone_service,
    tuya_service,
    wallet_service,
    zone_service,
)
from backend.services.billing_service import LockedRate, resolve_rate
from backend.services.device_type_service import DeviceTypeService
from backend.services.package_service import PackageService
from backend.services.printer_discovery import DiscoveredPrinter, discover_printers
from backend.services.staff_zone_service import StaffZoneService
from backend.services.wallet_service import WalletService
from backend.services.zone_service import ZoneService

__all__: list[str] = [
    "auth_service",
    "billing_service",
    "backup_service",
    "device_type_service",
    "inventory_service",
    "package_service",
    "peak_schedule_service",
    "pos_service",
    "printer_discovery",
    "remote_command_service",
    "reservation_service",
    "seat_service",
    "session_service",
    "shift_service",
    "staff_zone_service",
    "tuya_service",
    "wallet_service",
    "zone_service",
    "LockedRate",
    "resolve_rate",
    "PackageService",
    "WalletService",
    "ZoneService",
    "DeviceTypeService",
    "PeakScheduleService",
    "StaffZoneService",
    "DiscoveredPrinter",
    "discover_printers",
]
