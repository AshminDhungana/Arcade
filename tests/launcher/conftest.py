"""Pytest configuration for launcher tests."""

import sys
from pathlib import Path

# Ensure the project root (where launcher_theme.py lives) is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    """Register the 'display' marker for tests that need a display."""
    config.addinivalue_line(
        "markers", "display: test requires a display (skipped on headless CI)"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip display tests when no display is available."""
    has_display = _has_display()
    if not has_display:
        skip_display = pytest.mark.skip(reason="No display available (headless)")
        for item in items:
            if "display" in item.keywords:
                item.add_marker(skip_display)


def _has_display() -> bool:
    """Best-effort check for a usable display."""
    import os
    import sys

    if sys.platform == "win32":
        return True  # Windows usually has a display in CI
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


# Import pytest here to avoid circular import in pytest_configure
import pytest
