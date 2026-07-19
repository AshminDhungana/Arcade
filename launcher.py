"""Arcade Launcher - Tkinter GUI for license activation and server management.

Entry point for the Arcade server.  Checks the Ed25519 license before the
main window is shown, then routes to one of three screens:

* ActivationScreen - license missing/invalid/bound to another machine
* SetupWizard - license valid but arcade.config.json missing
* MainScreen - ready to start/stop the server
"""

from __future__ import annotations

import asyncio
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext
from typing import Any

import customtkinter as ctk

from backend.core.security import hash_pin
from backend.licensing.fingerprint import get_hardware_id
from backend.licensing.verify import LicenseError, LicenseResult, check_license
from launcher_theme import (
    S900,
)

# ---------------------------------------------------------------------------
# Error messages (SDD Section 16.7)
# ---------------------------------------------------------------------------

_LICENSE_ERROR_MESSAGES: dict[LicenseError, str] = {
    LicenseError.MISSING: (
        "No license file found.  Please purchase a license or contact support"
        " with your Hardware ID below."
    ),
    LicenseError.INVALID_SIGNATURE: (
        "This license file is not valid.  Please confirm you received it"
        " correctly, or contact support."
    ),
    LicenseError.HARDWARE_MISMATCH: (
        "This license is registered to a different machine.  Contact the seller"
        " with your Hardware ID below to get this license reissued."
    ),
    LicenseError.TRIAL_EXPIRED: (
        "Your trial period has ended.  Contact the seller to purchase a full license."
    ),
}


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------


def _db_path() -> Path:
    return Path(__file__).with_suffix("").parent / "backend" / "arcade.db"


def _write_license_status(
    payload: dict[str, Any], license_result: LicenseResult
) -> None:
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS license_status (
            id TEXT PRIMARY KEY,
            cafe_name TEXT NOT NULL,
            hardware_id TEXT NOT NULL,
            license_type TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            trial_expires_at TEXT,
            last_verified_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        "DELETE FROM license_status WHERE id = ?",
        ("current",),
    )
    cur.execute(
        """
        INSERT INTO license_status
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "current",
            payload["cafe_name"],
            payload["hardware_id"],
            payload["license_type"],
            payload["issue_date"],
            payload.get("trial_expires_at"),
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Root controller
# ---------------------------------------------------------------------------


class LauncherApp:
    """CustomTkinter application root.  Manages screen switching."""

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("Arcade Launcher")
        self.root.geometry("720x600")
        self.root.minsize(720, 600)
        self.root.configure(fg_color=["#F1F5F9", S900])
        self.current_screen: ctk.CTkFrame | None = None
        self._main_screen: MainScreen | None = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(
        self, screen_class: type[ctk.CTkFrame], *args: Any, **kwargs: Any
    ) -> None:
        if self.current_screen is not None:
            self.current_screen.destroy()
        # MyPy sees screen_class as ctk.CTkFrame, whose second positional arg is
        # cnf: dict | None. Cast to Any so the custom subclass constructor
        # (which takes a controller as second arg) type-checks correctly.
        _cls: Any = screen_class
        new_screen = _cls(self.root, self, *args, **kwargs)
        new_screen.pack(fill=tk.BOTH, expand=True)
        self.current_screen = new_screen

    # ------------------------------------------------------------------
    # Window close (FR-SYS-010)
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        if (
            self._main_screen is not None
            and self._main_screen._proc is not None
            and self._main_screen._proc.poll() is None
        ):
            ok = messagebox.askyesno(
                "Confirm Exit",
                "The Arcade server is still running. Closing the Launcher will "
                "stop the server. Are you sure?",
            )
            if not ok:
                return
            self._main_screen._stop_server()
        self.root.destroy()

    # ------------------------------------------------------------------
    # License routing (FR-SYS-008)
    # ------------------------------------------------------------------

    def _check_and_route(self) -> None:
        result = check_license()
        if result.ok:
            if Path("arcade.config.json").exists():
                self.show_screen(MainScreen)
                self._main_screen = self.current_screen  # type: ignore[assignment]
            else:
                self.show_screen(SetupWizard, result)
        else:
            self.show_screen(ActivationScreen, result)

    # ------------------------------------------------------------------
    # Entry hook
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()


# ---------------------------------------------------------------------------
# ActivationScreen
# ---------------------------------------------------------------------------


class ActivationScreen(tk.Frame):
    """Shown when the license check fails."""

    def __init__(
        self, parent: tk.Widget, controller: LauncherApp, result: LicenseResult
    ) -> None:
        super().__init__(parent, bg="#f5f5f5")
        self.controller = controller
        self.result = result
        self._build()

    def _build(self) -> None:
        # Title
        tk.Label(
            self,
            text="License Required",
            font=("Arial", 22, "bold"),
            bg="#f5f5f5",
            fg="#333",
        ).pack(pady=(30, 10))

        # Error box
        error = self.result.error or LicenseError.MISSING
        msg = _LICENSE_ERROR_MESSAGES.get(error, str(error))
        self.error_label = tk.Label(
            self,
            text=msg,
            wraplength=600,
            justify=tk.CENTER,
            bg="#f5f5f5",
            fg="#c33",
            font=("Arial", 11),
        )
        self.error_label.pack(pady=10)

        # Hardware ID section
        tk.Label(
            self,
            text="Hardware ID (give this to support):",
            bg="#f5f5f5",
            font=("Arial", 10, "bold"),
        ).pack(pady=(20, 5))

        self.hwid_var = tk.StringVar(value=get_hardware_id())
        entry = tk.Entry(
            self,
            textvariable=self.hwid_var,
            state="readonly",
            font=("Courier", 12),
            width=34,
        )
        entry.pack()

        # Browse button
        tk.Button(self, text="Browse for license.key …", command=self._browse).pack(
            pady=20
        )

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select license.key", filetypes=[("License files", "*.key")]
        )
        if path:
            dest = Path("license.key")
            try:
                # Copy (not move): the chosen file may live on another drive,
                # and we must not delete the user's original license.key.
                shutil.copy2(path, dest)
                # Re-check and re-route
                self.controller._check_and_route()
            except Exception as exc:
                messagebox.showerror("Error", f"Unable to copy license file:\n{exc}")


# ---------------------------------------------------------------------------
# SetupWizard
# ---------------------------------------------------------------------------


class SetupWizard(tk.Frame):
    """First-run wizard to generate arcade.config.json."""

    def __init__(
        self, parent: tk.Widget, controller: LauncherApp, license_result: LicenseResult
    ) -> None:
        super().__init__(parent, bg="#f5f5f5")
        self.controller = controller
        self.license_result = license_result
        self._build()

    def _build(self) -> None:
        tk.Label(
            self, text="Setup Wizard", font=("Arial", 20, "bold"), bg="#f5f5f5"
        ).pack(pady=15)

        # ── Cafe / Server ──
        frame = tk.Frame(self, bg="#f5f5f5")
        frame.pack(pady=5)

        self._cafe_name_var = tk.StringVar()
        tk.Label(frame, text="Cafe Name:", bg="#f5f5f5").grid(
            row=0, column=0, sticky="w"
        )
        tk.Entry(frame, textvariable=self._cafe_name_var, width=30).grid(
            row=0, column=1, padx=5
        )

        self._host_var = tk.StringVar(value="0.0.0.0")
        tk.Label(frame, text="Server IP:", bg="#f5f5f5").grid(
            row=1, column=0, sticky="w"
        )
        tk.Entry(frame, textvariable=self._host_var, width=30).grid(
            row=1, column=1, padx=5
        )

        self._port_var = tk.StringVar(value="8000")
        tk.Label(frame, text="Port:", bg="#f5f5f5").grid(row=2, column=0, sticky="w")
        tk.Entry(frame, textvariable=self._port_var, width=30).grid(
            row=2, column=1, padx=5
        )

        # ── Staff ──
        staff = tk.Frame(self, bg="#f5f5f5")
        staff.pack(pady=10)

        tk.Label(
            staff, text="--- Staff ---", bg="#f5f5f5", font=("Arial", 10, "bold")
        ).pack()

        self._admin_id_var = tk.StringVar(value="admin")
        tk.Label(staff, text="Admin Staff ID:", bg="#f5f5f5").pack(anchor="w")
        tk.Entry(staff, textvariable=self._admin_id_var, width=30).pack()

        self._admin_pin_var = tk.StringVar()
        tk.Label(staff, text="Admin PIN:", bg="#f5f5f5").pack(anchor="w", pady=(5, 0))
        tk.Entry(staff, textvariable=self._admin_pin_var, show="*", width=30).pack()

        self._cashier_id_var = tk.StringVar(value="cashier")
        tk.Label(staff, text="Cashier Staff ID:", bg="#f5f5f5").pack(
            anchor="w", pady=(5, 0)
        )
        tk.Entry(staff, textvariable=self._cashier_id_var, width=30).pack()

        self._cashier_pin_var = tk.StringVar()
        tk.Label(staff, text="Cashier PIN:", bg="#f5f5f5").pack(anchor="w", pady=(5, 0))
        tk.Entry(staff, textvariable=self._cashier_pin_var, show="*", width=30).pack()

        # ── Seats ──
        self._seat_count_var = tk.StringVar(value="8")
        tk.Label(self, text="Number of Seats:", bg="#f5f5f5").pack(pady=(10, 0))
        tk.Entry(self, textvariable=self._seat_count_var, width=10).pack()

        # ── Finish ──
        tk.Button(self, text="Finish", command=self._finish).pack(pady=20)

    def _seed_default_staff(self) -> None:
        """Best-effort: create the default admin + cashier in the DB.

        Runs in a background thread (DB + alembic can be slow) so the wizard UI
        stays responsive. Any failure is non-fatal: the server's startup
        self-heal (ensure_default_staff in main.py lifespan) covers it.
        """
        import logging
        import threading

        logger = logging.getLogger(__name__)

        def _run() -> None:
            from backend.core.bootstrap import ensure_default_staff
            from backend.core.config import load_config
            from backend.core.database import AsyncSessionLocal
            from backend.core.startup import run_migrations

            async def _bootstrap() -> None:
                await run_migrations()
                async with AsyncSessionLocal() as db:
                    # Read the config we just wrote (not the lru-cached getter).
                    await ensure_default_staff(db, settings=load_config())
                    await db.commit()

            try:
                asyncio.run(_bootstrap())
            except Exception as exc:  # noqa: BLE001 — best-effort, never block wizard
                logger.warning("Default staff seed skipped: %s", exc)

        threading.Thread(target=_run, daemon=True).start()

    def _finish(self) -> None:
        payload = self.license_result.payload or {}

        try:
            seat_count = int(self._seat_count_var.get())
        except ValueError:
            seat_count = 8

        # Build config matching backend.core.config.Settings
        config: dict[str, Any] = {
            "cafe_name": self._cafe_name_var.get()
            or payload.get("cafe_name", "Arcade"),
            "host": self._host_var.get() or "0.0.0.0",
            "port": int(self._port_var.get() or 8000),
            "admin_staff_id": self._admin_id_var.get() or "admin",
            "admin_pin_hash": hash_pin(self._admin_pin_var.get() or "admin"),
            "cashier_staff_id": self._cashier_id_var.get() or "cashier",
            "cashier_pin_hash": hash_pin(self._cashier_pin_var.get() or "cashier"),
            "jwt_secret": secrets.token_hex(32),
            "agent_secrets": {
                f"seat_{i + 1}": secrets.token_hex(32) for i in range(seat_count)
            },
        }

        # Write config
        Path("arcade.config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        # Write license_status row (FR-LIC-014)
        _write_license_status(payload, self.license_result)

        # Best-effort seed default admin + cashier into the DB now.
        self._seed_default_staff()

        # Route
        self.controller._check_and_route()


# ---------------------------------------------------------------------------
# MainScreen
# ---------------------------------------------------------------------------


class MainScreen(tk.Frame):
    """Main screen: server start/stop, logs, dashboard."""

    def __init__(self, parent: tk.Widget, controller: LauncherApp) -> None:
        super().__init__(parent, bg="#f5f5f5")
        self.controller = controller
        self._proc: subprocess.Popen[str] | None = None
        self._log_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._status_var = tk.StringVar(value="Stopped")
        self._build()

    def _build(self) -> None:
        # Title
        tk.Label(
            self, text="Arcade Server", font=("Arial", 20, "bold"), bg="#f5f5f5"
        ).pack(pady=15)

        # Status
        status_frame = tk.Frame(self, bg="#f5f5f5")
        status_frame.pack(pady=5)

        self._dot = tk.Canvas(
            status_frame, width=20, height=20, bg="#f5f5f5", highlightthickness=0
        )
        self._dot.pack(side=tk.LEFT, padx=(0, 5))
        self._dot_id = self._dot.create_oval(2, 2, 18, 18, fill="red")

        tk.Label(
            status_frame,
            textvariable=self._status_var,
            font=("Arial", 12),
            bg="#f5f5f5",
        ).pack(side=tk.LEFT)

        # Buttons
        btn_frame = tk.Frame(self, bg="#f5f5f5")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Start Server", command=self._start_server).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Stop Server", command=self._stop_server).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Open Dashboard", command=self._open_dashboard).pack(
            side=tk.LEFT, padx=5
        )

        # Logs
        tk.Label(
            self, text="Server Logs:", font=("Arial", 10, "bold"), bg="#f5f5f5"
        ).pack(pady=(10, 0), anchor="w", padx=10)
        self._log_text = scrolledtext.ScrolledText(
            self, height=15, state=tk.DISABLED, wrap=tk.WORD
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _append_log(self, line: str) -> None:
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, line)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _start_server(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return

        host = "0.0.0.0"
        port = 8000
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                host = cfg.get("host", "0.0.0.0")
                port = int(cfg.get("port", 8000))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass

        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                host,
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        self._status_var.set(f"Running at http://{host}:{port}")
        self._dot.itemconfig(self._dot_id, fill="green")

        self._stop_event.clear()
        self._log_thread = threading.Thread(target=self._stream_logs, daemon=True)
        self._log_thread.start()

    def _stream_logs(self) -> None:
        if self._proc is not None and self._proc.stdout is not None:
            for line in self._proc.stdout:
                if self._stop_event.is_set():
                    break
                self._append_log(line)

    def _stop_server(self) -> None:
        self._stop_event.set()
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._status_var.set("Stopped")
        self._dot.itemconfig(self._dot_id, fill="red")

    def _open_dashboard(self) -> None:
        host = "localhost"
        port = 8000
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                host = cfg.get("host", "localhost")
                port = int(cfg.get("port", 8000))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass
        webbrowser.open(f"http://{host}:{port}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = LauncherApp(root)
    app._check_and_route()
    app.run()


if __name__ == "__main__":
    main()
