"""Tests for cross-platform printer discovery service."""

import sys
from unittest.mock import AsyncMock

import pytest

from backend.services.printer_discovery import (
    DiscoveredPrinter,
    discover_printers,
)


class TestDiscoveredPrinter:
    def test_dataclass_creation(self):
        printer = DiscoveredPrinter(
            name="Test Printer",
            connection_type="usb",
            uri="usb://USB001",
            is_default=True,
            status="idle",
            location="Counter",
        )
        assert printer.name == "Test Printer"
        assert printer.connection_type == "usb"
        assert printer.uri == "usb://USB001"
        assert printer.is_default is True
        assert printer.status == "idle"
        assert printer.location == "Counter"


class TestDiscoverPrinters:
    @pytest.mark.asyncio
    async def test_dispatches_to_windows_on_win32(self, monkeypatch):
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        mock_result = [
            DiscoveredPrinter(
                name="Win Printer",
                connection_type="usb",
                uri="usb://USB001",
                is_default=False,
                status="idle",
            )
        ]
        monkeypatch.setattr(
            "backend.services.printer_discovery._discover_windows",
            AsyncMock(return_value=mock_result),
        )

        result = await discover_printers()
        assert result == mock_result

    @pytest.mark.asyncio
    async def test_dispatches_to_cups_on_non_windows(self, monkeypatch):
        if sys.platform == "win32":
            pytest.skip("Non-Windows test")

        mock_result = [
            DiscoveredPrinter(
                name="CUPS Printer",
                connection_type="network",
                uri="socket://192.168.1.50:9100",
                is_default=True,
                status="idle",
            )
        ]
        monkeypatch.setattr(
            "backend.services.printer_discovery._discover_cups",
            AsyncMock(return_value=mock_result),
        )

        result = await discover_printers()
        assert result == mock_result

    # Graceful degradation handled by ImportError catches inside


# _discover_windows/_discover_cups, verified by test_printer_discovery_imports.py
