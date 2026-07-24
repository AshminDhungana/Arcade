"""Verify platform-specific printer discovery dependencies are available."""

import sys

import pytest


def test_windows_dependencies_importable():
    """pywin32 and wmi import on Windows."""
    if sys.platform == "win32":
        import win32print
        import wmi

        # Basic API sanity check
        assert hasattr(win32print, "EnumPrinters")
        assert hasattr(win32print, "PRINTER_ENUM_LOCAL")
        assert hasattr(win32print, "PRINTER_ENUM_CONNECTIONS")
        assert hasattr(win32print, "GetDefaultPrinter")
        assert hasattr(wmi, "WMI")
    else:
        pytest.skip("Windows-only dependencies")


def test_cups_dependencies_importable():
    """pycups imports on non-Windows platforms."""
    if sys.platform != "win32":
        import cups

        # Verify the module imports and has expected attributes
        # Don't actually connect - no CUPS server in CI
        assert hasattr(cups, "Connection")
        assert hasattr(cups.Connection, "getPrinters")
        assert hasattr(cups.Connection, "getDefault")
    else:
        pytest.skip("CUPS not on Windows")
