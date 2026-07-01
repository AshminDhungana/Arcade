"""Tests for the Tkinter Launcher (launcher.py)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Tcl/Tk availability check (Windows venv sometimes missing tcl) -----------
# ---------------------------------------------------------------------------

_TK_AVAILABLE = False

try:
    import tkinter as _tk

    _tk_root = _tk.Tk()
    _tk_root.destroy()
    _TK_AVAILABLE = True
except Exception:
    _TK_AVAILABLE = False


@pytest.mark.skipif(not _TK_AVAILABLE, reason="Tcl/Tk not available")
class TestActivationScreen:
    def test_shows_error_for_missing_license(self) -> None:
        import tkinter as tk

        from backend.licensing.verify import LicenseError
        from launcher import ActivationScreen, LauncherApp

        root = tk.Tk()
        app = LauncherApp(root)
        with patch("launcher.check_license") as mock_check:
            result = type(
                "LicenseResult",
                (),
                {"ok": False, "error": LicenseError.MISSING, "payload": None},
            )()
            mock_check.return_value = result
            screen = ActivationScreen(root, app, result)  # type: ignore[arg-type]
            assert "no license file found" in screen.error_label.cget("text").lower()
        root.destroy()

    def test_shows_hardware_id(self) -> None:
        import tkinter as tk

        from launcher import ActivationScreen, LauncherApp

        root = tk.Tk()
        app = LauncherApp(root)
        with patch("launcher.check_license") as mock_check:
            with patch("launcher.get_hardware_id", return_value="a" * 32):
                result = type(
                    "LicenseResult",
                    (),
                    {
                        "ok": False,
                        "error": type("E", (), {"value": "missing"})(),
                        "payload": None,
                    },
                )()
                mock_check.return_value = result
                screen = ActivationScreen(root, app, result)  # type: ignore[arg-type]
                hwid = screen.hwid_var.get()
                assert len(hwid) == 32
        root.destroy()


@pytest.mark.skipif(not _TK_AVAILABLE, reason="Tcl/Tk not available")
class TestSetupWizard:
    def test_writes_arcade_config_json(self, tmp_path: Any, monkeypatch: Any) -> None:
        import tkinter as tk

        from launcher import LauncherApp, SetupWizard

        root = tk.Tk()
        app = LauncherApp(root)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("launcher._db_path", lambda: tmp_path / "arcade.db")

        result = type(
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
        wizard = SetupWizard(root, app, result)  # type: ignore[arg-type]
        wizard._cafe_name_var.set("Galaxy Cafe")
        wizard._host_var.set("0.0.0.0")
        wizard._port_var.set("8000")
        wizard._admin_id_var.set("admin01")
        wizard._admin_pin_var.set("1234")
        wizard._cashier_id_var.set("cash01")
        wizard._cashier_pin_var.set("5678")
        wizard._seat_count_var.set("4")
        wizard._finish()

        config = json.loads(Path("arcade.config.json").read_text())
        assert config["cafe_name"] == "Galaxy Cafe"
        assert config["host"] == "0.0.0.0"
        assert config["port"] == 8000
        assert "admin_pin_hash" in config
        assert "cashier_pin_hash" in config
        assert len(config["agent_secrets"]) == 4
        for v in config["agent_secrets"].values():
            assert len(v) == 64
        root.destroy()

    def test_writes_license_status_to_db(self, tmp_path: Any, monkeypatch: Any) -> None:
        import tkinter as tk

        from launcher import LauncherApp, SetupWizard

        root = tk.Tk()
        app = LauncherApp(root)
        db_path = tmp_path / "arcade.db"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("launcher._db_path", lambda: db_path)

        result = type(
            "R",
            (),
            {
                "ok": True,
                "payload": {
                    "cafe_name": "Test Cafe",
                    "hardware_id": "b" * 32,
                    "license_type": "TRIAL",
                    "issue_date": "2026-01-01",
                    "trial_expires_at": "2026-12-31",
                },
            },
        )()
        wizard = SetupWizard(root, app, result)  # type: ignore[arg-type]
        wizard._cafe_name_var.set("Test Cafe")
        wizard._finish()

        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute(
            "SELECT cafe_name, hardware_id, license_type FROM license_status "
            "WHERE id='current'",
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "Test Cafe"
        assert row[1] == "b" * 32
        assert row[2] == "TRIAL"
        root.destroy()


@pytest.mark.skipif(not _TK_AVAILABLE, reason="Tcl/Tk not available")
class TestMainScreen:
    def test_server_start_button_spawns_subprocess(self) -> None:
        import tkinter as tk

        from launcher import LauncherApp, MainScreen

        root = tk.Tk()
        app = LauncherApp(root)
        screen = MainScreen(root, app)  # type: ignore[arg-type]
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc
            screen._start_server()
            mock_popen.assert_called_once()
            args, _ = mock_popen.call_args
            assert "uvicorn" in args[0]
        root.destroy()

    def test_server_stop_sends_sigterm(self) -> None:
        import tkinter as tk

        from launcher import LauncherApp, MainScreen

        root = tk.Tk()
        app = LauncherApp(root)
        screen = MainScreen(root, app)  # type: ignore[arg-type]
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc
            screen._start_server()
            screen._stop_server()
            mock_proc.terminate.assert_called_once()
        root.destroy()
