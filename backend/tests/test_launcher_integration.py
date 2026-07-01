"""Integration tests for the Tkinter Launcher.

Covers full flow: license check -> screen routing -> config writing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch


class TestLauncherEndToEnd:
    def test_missing_license_shows_activation_screen(self, monkeypatch: Any) -> None:
        import tkinter as tk

        from backend.licensing.verify import LicenseError
        from launcher import ActivationScreen, LauncherApp

        root = tk.Tk()
        app = LauncherApp(root)

        with patch("launcher.check_license") as mock_check:
            mock_check.return_value = type(
                "R", (), {"ok": False, "error": LicenseError.MISSING, "payload": None}
            )()
            app._check_and_route()
            assert isinstance(app.current_screen, ActivationScreen)

        root.destroy()

    def test_valid_license_no_config_shows_wizard(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        import tkinter as tk

        from launcher import LauncherApp, SetupWizard

        root = tk.Tk()
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
            assert isinstance(app.current_screen, SetupWizard)

        root.destroy()
