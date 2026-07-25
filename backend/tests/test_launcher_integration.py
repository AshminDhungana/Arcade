"""Integration tests for the CustomTkinter Launcher.

Covers full flow: license check -> screen routing -> config writing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Tcl/Tk/CustomTkinter availability check
# ---------------------------------------------------------------------------

_TK_AVAILABLE = False
_DISPLAY_AVAILABLE = False

try:
    import customtkinter as ctk

    _ctk_root = ctk.CTk()
    _ctk_root.withdraw()  # Don't show window
    _ctk_root.update()
    _ctk_root.destroy()
    _TK_AVAILABLE = True
    _DISPLAY_AVAILABLE = True
except Exception:
    _TK_AVAILABLE = False
    _DISPLAY_AVAILABLE = False


@pytest.mark.skipif(not _TK_AVAILABLE, reason="CustomTkinter/Tcl/Tk not available")
@pytest.mark.skipif(not _DISPLAY_AVAILABLE, reason="No display available (headless CI)")
class TestLauncherEndToEnd:
    def test_missing_license_shows_activation_screen(self, monkeypatch: Any) -> None:
        import customtkinter as ctk

        from backend.licensing.verify import LicenseError
        from launcher import ActivationScreen, LauncherApp

        # Mock load_logo and _gradient to return None (avoids CTkImage/pyimage
        # issues in tests)
        # launcher.py imports it as: from launcher_theme import load_logo
        # Patch where it's USED (launcher module), not where defined
        monkeypatch.setattr("launcher.load_logo", lambda *a, **k: None)
        monkeypatch.setattr("launcher.LauncherApp._gradient", lambda *a, **k: None)
        # Force reduced_motion so screen_transition runs swap() synchronously
        # launcher.py: from launcher_motion import prefers_reduced_motion
        # _reduced_motion = prefers_reduced_motion() called at
        # LauncherApp.__init__ line 841
        # Patch the name as used in the launcher module
        monkeypatch.setattr("launcher.prefers_reduced_motion", lambda: True)

        root = ctk.CTk()
        root.withdraw()  # Don't show window
        root.update()
        app = LauncherApp(root)

        with patch("launcher.check_license") as mock_check:
            mock_check.return_value = type(
                "R",
                (),
                {
                    "ok": False,
                    "error": LicenseError.MISSING,
                    "payload": None,
                },
            )()
            app._check_and_route()
            # _reduced_motion is True from patched prefers_reduced_motion(),
            # so swap is synchronous
            assert isinstance(app.current_screen, ActivationScreen)

        root.destroy()

    def test_valid_license_no_config_shows_wizard(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        import customtkinter as ctk

        from launcher import LauncherApp, SetupWizard

        # Mock load_logo and _gradient to return None (avoids CTkImage/pyimage
        # issues in tests)
        monkeypatch.setattr("launcher.load_logo", lambda *a, **k: None)
        monkeypatch.setattr("launcher.LauncherApp._gradient", lambda *a, **k: None)
        # Force reduced_motion so screen_transition runs swap() synchronously
        # launcher.py: from launcher_motion import prefers_reduced_motion
        monkeypatch.setattr("launcher.prefers_reduced_motion", lambda: True)

        root = ctk.CTk()
        root.withdraw()  # Don't show window
        root.update()
        app = LauncherApp(root)
        monkeypatch.chdir(tmp_path)

        with patch("launcher.check_license") as mock_check:
            mock_check.return_value = type(
                "R",
                (),
                {
                    "ok": True,
                    "payload": {
                        "cafe_name": "Test",
                        "hardware_id": "a" * 32,
                        "license_type": "PERPETUAL",
                        "issue_date": "2026-01-01",
                    },
                },
            )()
            app._check_and_route()
            # _reduced_motion is True from patched prefers_reduced_motion(),
            # so swap is synchronous
            assert isinstance(app.current_screen, SetupWizard)

        root.destroy()
