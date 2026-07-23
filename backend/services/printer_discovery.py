"""Cross-platform printer discovery service."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Literal


@dataclass
class DiscoveredPrinter:
    """Unified printer representation across platforms."""

    name: str
    connection_type: Literal["usb", "network"]
    uri: str
    is_default: bool
    status: Literal["idle", "printing", "error", "unknown"]
    location: str | None = None


async def discover_printers() -> list[DiscoveredPrinter]:
    """Discover all OS-installed printers."""
    if sys.platform == "win32":
        return await _discover_windows()
    else:
        return await _discover_cups()


async def _discover_windows() -> list[DiscoveredPrinter]:
    """Windows: win32print.EnumPrinters + WMI for metadata."""
    try:
        import win32print
        import wmi
    except ImportError:
        return []

    printers: list[DiscoveredPrinter] = []

    try:
        default_name = win32print.GetDefaultPrinter()
    except Exception:
        default_name = ""

    # EnumPrinters level=2 returns PRINTER_INFO_2 structs
    printer_info_list = win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS,
        None,
        2,
    )

    c = wmi.WMI()

    for p in printer_info_list:
        name = p["pPrinterName"]
        port_name = p["pPortName"]
        attributes = p["Attributes"]

        is_network = bool(attributes & win32print.PRINTER_ATTRIBUTE_NETWORK)
        conn_type: Literal["usb", "network"] = "network" if is_network else "usb"

        # Build URI from port name
        if is_network:
            # Port name like "IP_192.168.1.50" or "192.168.1.50"
            ip = port_name.replace("IP_", "")
            uri = f"socket://{ip}:9100"
        else:
            # USB port like "USB001"
            uri = f"usb://{port_name}"

        # Try to get location from WMI
        location = None
        try:
            for wmi_printer in c.Win32_Printer(Name=name):
                location = wmi_printer.Location or None
                break
        except Exception:  # noqa: S110 - WMI query optional
            pass

        printers.append(
            DiscoveredPrinter(
                name=name,
                connection_type=conn_type,
                uri=uri,
                is_default=(name == default_name),
                status="idle",
                location=location,
            )
        )

    return printers


async def _discover_cups() -> list[DiscoveredPrinter]:
    """macOS/Linux: CUPS via pycups."""
    try:
        import cups
    except ImportError:
        return []

    printers: list[DiscoveredPrinter] = []

    try:
        conn = cups.Connection()
        cups_printers = conn.getPrinters()
        default_name = conn.getDefault()
    except Exception:
        return []

    for name, attrs in cups_printers.items():
        device_uri = attrs.get("device-uri", "")

        # Determine connection type from URI scheme
        if device_uri.startswith("usb://"):
            conn_type: Literal["usb", "network"] = "usb"
        elif device_uri.startswith(
            ("socket://", "ipp://", "http://", "https://", "lpd://")
        ):
            conn_type = "network"
        else:
            conn_type = "network"  # default fallback

        printers.append(
            DiscoveredPrinter(
                name=name,
                connection_type=conn_type,
                uri=device_uri,
                is_default=(name == default_name),
                status="idle",
                location=attrs.get("printer-location") or None,
            )
        )

    return printers
