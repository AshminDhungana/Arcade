"""Arcade Launcher - Tkinter GUI for license activation and server management.

Entry point for the Arcade server. Checks the Ed25519 license before the
main window is shown, then routes to one of three screens wrapped in a
persistent shell (topbar + content + footer status bar):

* ActivationScreen - license missing/invalid/bound to another machine
* SetupWizard      - license valid but arcade.config.json missing
* MainScreen       - ready to start/stop the server
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from backend.core.security import hash_pin
from backend.licensing.fingerprint import get_hardware_id
from backend.licensing.verify import LicenseError, LicenseResult, check_license
from launcher_motion import animate_pill, prefers_reduced_motion, screen_transition
from launcher_theme import (
    BTN_HEIGHT,
    COLORS,
    GRADIENT_STRIP,
    RADIUS,
    SPACING,
    load_logo,
    make_fonts,
)
from launcher_widgets import (
    Card,
    LabeledField,
    StatusBar,
    StepIndicator,
    screen_title,
    show_toast,
)

# Default bind address/port for the Arcade server. Overridable per-install
# via the setup wizard; kept here as the single source of truth so the
# wizard default, fallbacks, and placeholders can't drift apart.
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8741

# ---------------------------------------------------------------------------
# Error messages (SDD Section 16.7)
# ---------------------------------------------------------------------------

_LICENSE_ERROR_MESSAGES: dict[LicenseError, str] = {
    LicenseError.MISSING: (
        "No license file found. Please purchase a license or contact support "
        "with your Hardware ID below."
    ),
    LicenseError.INVALID_SIGNATURE: (
        "This license file is not valid. Please confirm you received it "
        "correctly, or contact support."
    ),
    LicenseError.HARDWARE_MISMATCH: (
        "This license is registered to a different machine. Contact the seller "
        "with your Hardware ID below to get this license reissued."
    ),
    LicenseError.TRIAL_EXPIRED: (
        "Your trial period has ended. Contact the seller to purchase a full license."
    ),
}

_ERROR_HEADLINES: dict[LicenseError, str] = {
    LicenseError.MISSING: "No License Found",
    LicenseError.INVALID_SIGNATURE: "License Invalid",
    LicenseError.HARDWARE_MISMATCH: "Wrong Machine",
    LicenseError.TRIAL_EXPIRED: "Trial Expired",
}

_log = logging.getLogger(__name__)


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
    cur.execute("DELETE FROM license_status WHERE id = ?", ("current",))
    cur.execute(
        "INSERT INTO license_status VALUES (?, ?, ?, ?, ?, ?, ?)",
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


def _center_window(root: ctk.CTk, width: int, height: int) -> None:
    """Center the window on the screen."""
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")


class _BaseScreen(ctk.CTkFrame):  # type: ignore[misc]
    """Base screen: transparent so it blends with the shell's content area."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        controller: LauncherApp,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)


# ---------------------------------------------------------------------------
# ActivationScreen
# ---------------------------------------------------------------------------


class ActivationScreen(_BaseScreen):
    """Shown when the license check fails."""

    def __init__(
        self, parent: ctk.CTkBaseClass, controller: LauncherApp, result: LicenseResult
    ) -> None:
        super().__init__(parent, controller)
        self.result = result
        self._build()

    def _build(self) -> None:
        f = self.controller.fonts
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(7, weight=1)

        screen_title(self, f, "License Activation Required").grid(
            row=0,
            column=0,
            padx=SPACING["xl"],
            pady=(SPACING["lg"], SPACING["md"]),
            sticky="ew",
        )

        error = self.result.error or LicenseError.MISSING
        msg = _LICENSE_ERROR_MESSAGES.get(error, str(error))
        card = Card(self)
        card.grid(
            row=1, column=0, padx=SPACING["xl"], pady=(0, SPACING["md"]), sticky="ew"
        )
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="⚠ " + _ERROR_HEADLINES.get(error, "License Required"),
            font=f["h2"],
            text_color=COLORS["error"],
            wraplength=540,
        ).grid(
            row=0,
            column=0,
            padx=SPACING["lg"],
            pady=(SPACING["md"], SPACING["xs"]),
            sticky="ew",
        )
        ctk.CTkLabel(
            card,
            text=msg,
            font=f["body"],
            text_color=COLORS["text_primary"],
            wraplength=540,
            justify="center",
        ).grid(
            row=1, column=0, padx=SPACING["lg"], pady=(0, SPACING["xs"]), sticky="ew"
        )
        ctk.CTkLabel(
            card,
            text="Purchase a license or contact support with your Hardware ID below.",
            font=f["caption"],
            text_color=COLORS["text_secondary"],
            wraplength=540,
        ).grid(
            row=2, column=0, padx=SPACING["lg"], pady=(0, SPACING["md"]), sticky="ew"
        )

        hwid_frame = ctk.CTkFrame(self, fg_color="transparent")
        hwid_frame.grid(
            row=2, column=0, padx=SPACING["xl"], pady=(0, SPACING["sm"]), sticky="ew"
        )
        hwid_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hwid_frame,
            text="Your Hardware ID:",
            font=f["body"],
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=0, sticky="w", pady=(0, SPACING["xs"]))
        self.hwid_var = tk.StringVar(value=get_hardware_id())
        hwid_entry = ctk.CTkEntry(
            hwid_frame,
            textvariable=self.hwid_var,
            state="readonly",
            font=f["mono"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        hwid_entry.grid(row=1, column=0, sticky="ew")
        copy_btn = ctk.CTkButton(
            hwid_frame,
            text="Copy Hardware ID",
            command=self._copy_hwid,
            font=f["body_bold"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        copy_btn.grid(row=2, column=0, pady=(SPACING["sm"], 0), sticky="ew")

        ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).grid(
            row=3, column=0, padx=SPACING["xl"], pady=SPACING["md"], sticky="ew"
        )

        ctk.CTkLabel(
            self,
            text="Have a license.key file?",
            font=f["h2"],
            text_color=COLORS["text_primary"],
        ).grid(row=4, column=0, padx=SPACING["xl"], pady=(0, SPACING["sm"]))
        browse_btn = ctk.CTkButton(
            self,
            text="Browse for license.key …",
            command=self._browse,
            font=f["body_bold"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["accent_fill"],
            hover_color=COLORS["accent_fill_hover"],
            text_color=COLORS["text_on_accent"],
        )
        browse_btn.grid(
            row=5, column=0, padx=SPACING["xl"], pady=(0, SPACING["lg"]), sticky="ew"
        )

    def _copy_hwid(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.hwid_var.get())
        show_toast(self.controller, "Hardware ID copied", kind="info")

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select license.key", filetypes=[("License files", "*.key")]
        )
        if path:
            dest = Path("license.key")
            try:
                # Copy (not move): the chosen file may live on another drive,
                # and the user should keep their original license.key.
                shutil.copy2(path, dest)
                self.controller._check_and_route()
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Error", f"Unable to copy license file:\n{exc}")


# ---------------------------------------------------------------------------
# SetupWizard
# ---------------------------------------------------------------------------


class SetupWizard(_BaseScreen):
    """First-run wizard to generate arcade.config.json."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        controller: LauncherApp,
        license_result: LicenseResult,
    ) -> None:
        super().__init__(parent, controller)
        self.license_result = license_result
        self._fields: list[LabeledField] = []
        self._build()

    def _build(self) -> None:
        f = self.controller.fonts
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)

        screen_title(
            self, f, "First-Time Setup", subtitle="Configure your Arcade server"
        ).grid(
            row=0,
            column=0,
            padx=SPACING["xl"],
            pady=(SPACING["lg"], SPACING["sm"]),
            sticky="ew",
        )

        self.indicator = StepIndicator(self, f, ["Café", "Staff", "Seats"])
        self.indicator.grid(
            row=1, column=0, padx=SPACING["xl"], pady=(0, SPACING["md"]), sticky="ew"
        )

        self.form = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self.form.grid(
            row=2, column=0, padx=SPACING["xl"], pady=SPACING["sm"], sticky="nsew"
        )
        self.form.grid_columnconfigure(0, weight=1)

        self._cafe_name_var = ctk.StringVar()
        self._host_var = ctk.StringVar(value=DEFAULT_HOST)
        self._port_var = ctk.StringVar(value=str(DEFAULT_PORT))
        self._admin_id_var = ctk.StringVar(value="admin")
        self._admin_pin_var = ctk.StringVar()
        self._cashier_id_var = ctk.StringVar(value="cashier")
        self._cashier_pin_var = ctk.StringVar()
        self._seat_count_var = ctk.StringVar(value="8")

        row = 0
        row = self._section(
            row,
            "Café & Server",
            0,
            "Basic identity and network settings for this server.",
            [
                ("Café Name", self._cafe_name_var, {"placeholder": "My Arcade"}),
                ("Server IP", self._host_var, {"placeholder": DEFAULT_HOST}),
                ("Port", self._port_var, {"placeholder": str(DEFAULT_PORT)}),
            ],
        )
        row = self._section(
            row,
            "Staff Accounts",
            1,
            "Create the default admin and cashier accounts. PINs are hashed.",
            [
                ("Admin Staff ID", self._admin_id_var, {}),
                (
                    "Admin PIN",
                    self._admin_pin_var,
                    {"show": "●", "placeholder": "4–6 digits"},
                ),
                ("Cashier Staff ID", self._cashier_id_var, {}),
                (
                    "Cashier PIN",
                    self._cashier_pin_var,
                    {"show": "●", "placeholder": "4–6 digits"},
                ),
            ],
        )
        row = self._section(
            row,
            "Seats",
            2,
            "Each seat gets a unique agent secret for secure WebSocket auth.",
            [("Number of Seats", self._seat_count_var, {})],
        )

        ctk.CTkButton(
            self,
            text="Finish Setup",
            command=self._finish,
            font=f["body_bold"],
            height=BTN_HEIGHT + 4,
            corner_radius=RADIUS,
            fg_color=COLORS["accent_fill"],
            hover_color=COLORS["accent_fill_hover"],
            text_color=COLORS["text_on_accent"],
        ).grid(
            row=3,
            column=0,
            padx=SPACING["xl"],
            pady=(SPACING["sm"], SPACING["lg"]),
            sticky="ew",
        )

    def _section(
        self,
        row: int,
        title: str,
        step_idx: int,
        hint: str,
        fields: list[tuple[str, ctk.StringVar, dict[str, Any]]],
    ) -> int:
        f = self.controller.fonts
        card = Card(self.form)
        card.grid(row=row, column=0, padx=0, pady=(0, SPACING["md"]), sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=f["h2"], text_color=COLORS["accent"]).grid(
            row=0,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["md"], SPACING["xs"]),
        )
        ctk.CTkLabel(
            card,
            text=hint,
            font=f["caption"],
            text_color=COLORS["text_secondary"],
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        r = 2
        for label, var, opts in fields:
            field = LabeledField(card, label, fonts=f, **opts)
            field.entry.configure(textvariable=var)
            field.grid(
                row=r,
                column=0,
                padx=SPACING["lg"],
                pady=(0, SPACING["sm"]),
                sticky="ew",
            )
            field.entry.bind(
                "<FocusIn>", lambda _e, i=step_idx: self.indicator.set_active(i)
            )
            self._fields.append(field)
            r += 1
        return row + 1

    def _validate(self) -> bool:
        ok = True
        for var, label in [
            (self._cafe_name_var, "Café Name"),
            (self._admin_id_var, "Admin Staff ID"),
            (self._cashier_id_var, "Cashier Staff ID"),
            (self._seat_count_var, "Number of Seats"),
        ]:
            if not var.get().strip():
                show_toast(self.controller, f"{label} is required", kind="error")
                ok = False
        for pin_var, who in [
            (self._admin_pin_var, "Admin"),
            (self._cashier_pin_var, "Cashier"),
        ]:
            pin = pin_var.get()
            if pin and not (pin.isdigit() and 4 <= len(pin) <= 6):
                show_toast(
                    self.controller, f"{who} PIN must be 4–6 digits", kind="error"
                )
                ok = False
        try:
            if int(self._seat_count_var.get()) < 1:
                raise ValueError
        except ValueError:
            show_toast(
                self.controller,
                "Number of Seats must be a positive integer",
                kind="error",
            )
            ok = False
        return ok

    def _seed_default_staff(self) -> None:
        """Best-effort: create the default admin + cashier in the DB."""

        def _run() -> None:
            from backend.core.bootstrap import ensure_default_staff
            from backend.core.config import load_config
            from backend.core.database import AsyncSessionLocal
            from backend.core.startup import run_migrations

            async def _bootstrap() -> None:
                await run_migrations()
                async with AsyncSessionLocal() as db:
                    await ensure_default_staff(db, settings=load_config())
                    await db.commit()

            try:
                asyncio.run(_bootstrap())
            except Exception as exc:  # noqa: BLE001
                _log.warning("Default staff seed skipped: %s", exc)

        threading.Thread(target=_run, daemon=True).start()

    def _finish(self) -> None:
        if not self._validate():
            return
        payload = self.license_result.payload or {}
        try:
            seat_count = int(self._seat_count_var.get())
        except ValueError:
            seat_count = 8
        config: dict[str, Any] = {
            "cafe_name": self._cafe_name_var.get()
            or payload.get("cafe_name", "Arcade"),
            "host": self._host_var.get() or DEFAULT_HOST,
            "port": int(self._port_var.get() or DEFAULT_PORT),
            "admin_staff_id": self._admin_id_var.get() or "admin",
            "admin_pin_hash": hash_pin(self._admin_pin_var.get() or "admin"),
            "cashier_staff_id": self._cashier_id_var.get() or "cashier",
            "cashier_pin_hash": hash_pin(self._cashier_pin_var.get() or "cashier"),
            "jwt_secret": secrets.token_hex(32),
            "agent_secrets": {
                f"seat_{i + 1}": secrets.token_hex(32) for i in range(seat_count)
            },
        }
        Path("arcade.config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        _write_license_status(payload, self.license_result)
        self._seed_default_staff()
        self.controller._check_and_route()


# ---------------------------------------------------------------------------
# MainScreen
# ---------------------------------------------------------------------------


class MainScreen(_BaseScreen):
    """Main screen: server start/stop, logs, dashboard."""

    def __init__(self, parent: ctk.CTkBaseClass, controller: LauncherApp) -> None:
        super().__init__(parent, controller)
        self._proc: subprocess.Popen[str] | None = None
        self._log_thread: threading.Thread | None = None
        self._health_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._logs_started = False
        self._server_host = DEFAULT_HOST
        self._server_port = DEFAULT_PORT
        self._build()

    def _build(self) -> None:
        f = self.controller.fonts
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)

        screen_title(self, f, "Server Control").grid(
            row=0,
            column=0,
            padx=SPACING["xl"],
            pady=(SPACING["lg"], SPACING["md"]),
            sticky="ew",
        )

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(
            row=1, column=0, padx=SPACING["xl"], pady=(0, SPACING["sm"]), sticky="ew"
        )
        status_frame.grid_columnconfigure(1, weight=1)
        self._pill = ctk.CTkLabel(
            status_frame,
            text="■  Stopped",
            font=f["body_bold"],
            text_color=COLORS["text_on_accent"],
            height=28,
            corner_radius=14,
            fg_color=COLORS["error_fill"],
            padx=14,
        )
        self._pill.grid(row=0, column=0, padx=(0, SPACING["md"]), sticky="w")
        ctk.CTkLabel(
            status_frame,
            text="Server status",
            font=f["body"],
            text_color=COLORS["text_secondary"],
        ).grid(row=0, column=1, sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(
            row=2, column=0, padx=SPACING["xl"], pady=(0, SPACING["sm"]), sticky="ew"
        )
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self._start_btn = ctk.CTkButton(
            btn_frame,
            text="Start Server",
            command=self._start_server,
            font=f["body_bold"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["success_fill"],
            hover_color=COLORS["success_fill"][1],
            text_color=COLORS["text_on_accent"],
        )
        self._start_btn.grid(row=0, column=0, padx=(0, SPACING["xs"]), sticky="ew")
        self._stop_btn = ctk.CTkButton(
            btn_frame,
            text="Stop Server",
            command=self._stop_server,
            font=f["body_bold"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["error_fill"],
            hover_color=COLORS["error_fill"][1],
            text_color=COLORS["text_on_accent"],
            state="disabled",
        )
        self._stop_btn.grid(row=0, column=1, padx=SPACING["xs"], sticky="ew")
        self._dashboard_btn = ctk.CTkButton(
            btn_frame,
            text="Open Dashboard",
            command=self._open_dashboard,
            font=f["body_bold"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            state="disabled",
        )
        self._dashboard_btn.grid(row=0, column=2, padx=(SPACING["xs"], 0), sticky="ew")

        log_card = Card(self)
        log_card.grid(
            row=3,
            column=0,
            padx=SPACING["xl"],
            pady=(SPACING["sm"], SPACING["lg"]),
            sticky="nsew",
        )
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            log_card,
            text="Server Logs",
            font=f["h2"],
            text_color=COLORS["text_primary"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["md"], SPACING["xs"]),
        )
        self._log_text = ctk.CTkTextbox(
            log_card,
            state=tk.DISABLED,
            wrap="word",
            font=f["mono"],
            fg_color=COLORS["bg_primary"],
            text_color=COLORS["text_primary"],
            border_width=0,
        )
        self._log_text.grid(
            row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=(0, SPACING["lg"])
        )
        self._log_text.insert(
            "0.0", "Server logs will appear here once you start the server."
        )

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _append_log(self, line: str) -> None:
        if not self._logs_started:
            self._log_text.configure(state=tk.NORMAL)
            self._log_text.delete("0.0", tk.END)
            self._log_text.configure(state=tk.DISABLED)
            self._logs_started = True
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, line)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _set_status(self, glyph: str, text: str, color_token: str) -> None:
        animate_pill(
            self._pill,
            COLORS[color_token],
            glyph,
            text,
            reduced=self.controller._reduced_motion,
        )

    def _start_server(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        self._server_host = DEFAULT_HOST
        self._server_port = DEFAULT_PORT
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                self._server_host = cfg.get("host", DEFAULT_HOST)
                self._server_port = int(cfg.get("port", DEFAULT_PORT))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass
        self._proc = subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                self._server_host,
                "--port",
                str(self._server_port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        status_msg = f"Running at http://{self._server_host}:{self._server_port}"
        self._set_status("●", status_msg, "success_fill")
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._dashboard_btn.configure(state="disabled")
        show_toast(self.controller, "Server started", kind="success")
        self._stop_event.clear()
        self._log_thread = threading.Thread(target=self._stream_logs, daemon=True)
        self._log_thread.start()
        # Start health check polling to enable dashboard button when server is ready
        self._health_thread = threading.Thread(target=self._poll_health, daemon=True)
        self._health_thread.start()

    def _stream_logs(self) -> None:
        if self._proc is not None and self._proc.stdout is not None:
            for line in self._proc.stdout:
                if self._stop_event.is_set():
                    break
                self._append_log(line)

    def _poll_health(self) -> None:
        """Poll /health until it responds 200, then enable dashboard button."""
        max_attempts = 60  # 30 seconds max (0.5s intervals)
        attempt = 0
        while attempt < max_attempts and not self._stop_event.is_set():
            try:
                url = f"http://127.0.0.1:{self._server_port}/health"
                req = urllib.request.Request(url, method="GET")  # noqa: S310
                with urllib.request.urlopen(req, timeout=2) as resp:  # noqa: S310
                    if resp.status == 200:
                        # Server is healthy: enable dashboard button on main thread
                        self._root().after(
                            0,
                            lambda: self._dashboard_btn.configure(state="normal"),
                        )
                        return
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                OSError,
            ):
                pass
            attempt += 1
            time.sleep(0.5)
        # If we exit without success, button stays disabled

    def _stop_server(self) -> None:
        self._stop_event.set()
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._set_status("■", "Stopped", "error_fill")
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._dashboard_btn.configure(state="disabled")
        show_toast(self.controller, "Server stopped", kind="error")

    def _open_dashboard(self) -> None:
        host = "localhost"
        port = DEFAULT_PORT
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                host = cfg.get("host", "localhost")
                port = int(cfg.get("port", DEFAULT_PORT))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass
        webbrowser.open(f"http://{host}:{port}")


# ---------------------------------------------------------------------------
# Root controller
# ---------------------------------------------------------------------------


class LauncherApp:
    """CustomTkinter application root. Manages the shell and screen switching."""

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("Arcade Launcher")
        self.root.geometry("780x640")
        self.root.minsize(720, 600)
        self.root.configure(fg_color=COLORS["bg_primary"])
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.fonts = make_fonts(ctk)
        self._reduced_motion = prefers_reduced_motion()
        self.current_screen: ctk.CTkFrame | None = None
        self._main_screen: MainScreen | None = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_topbar()
        self._build_content()
        self._build_footer()
        self._apply_appearance(self._load_appearance())
        _center_window(self.root, 780, 640)

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self.root, fg_color=COLORS["bg_secondary"], corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        logo = load_logo(40)
        if logo is not None:
            ctk.CTkLabel(bar, image=logo, text="").grid(
                row=0,
                column=0,
                rowspan=2,
                padx=(SPACING["lg"], SPACING["sm"]),
                pady=SPACING["md"],
            )
        ctk.CTkLabel(
            bar, text="ARCADE", font=self.fonts["h1"], text_color=COLORS["accent"]
        ).grid(row=0, column=1, sticky="w", pady=(SPACING["md"], 0))
        ctk.CTkLabel(
            bar,
            text="Server Launcher",
            font=self.fonts["caption"],
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=1, sticky="w")
        self.appearance = ctk.CTkOptionMenu(
            bar,
            values=["System", "Dark", "Light"],
            width=110,
            command=self._on_appearance,
            font=self.fonts["body"],
            fg_color=COLORS["bg_tertiary"],
            button_color=COLORS["accent_fill"],
            button_hover_color=COLORS["accent_fill_hover"],
            text_color=COLORS["text_primary"],
        )
        self.appearance.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="e",
            padx=(0, SPACING["lg"]),
            pady=SPACING["md"],
        )
        grad = self._gradient()
        if grad is not None:
            ctk.CTkLabel(bar, image=grad, text="").grid(
                row=2, column=0, columnspan=3, sticky="ew"
            )
        else:
            ctk.CTkFrame(bar, height=3, fg_color=COLORS["accent_fill"]).grid(
                row=2, column=0, columnspan=3, sticky="ew"
            )

    def _gradient(self) -> Any:
        if not GRADIENT_STRIP.is_file():
            return None
        try:
            from PIL import Image

            img = Image.open(GRADIENT_STRIP)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(900, 3))
        except Exception:  # noqa: BLE001
            return None

    def _build_content(self) -> None:
        self.content = ctk.CTkFrame(
            self.root, fg_color=COLORS["bg_primary"], corner_radius=0
        )
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _build_footer(self) -> None:
        self.status = StatusBar(self.root, self.fonts)
        self.status.grid(row=2, column=0, sticky="ew")
        self.status.set("Ready", "info")

    # ------------------------------------------------------------------
    # Appearance
    # ------------------------------------------------------------------

    def _load_appearance(self) -> str:
        try:
            data = json.loads(Path("launcher.state.json").read_text(encoding="utf-8"))
            mode = data.get("appearance", "System")
            return mode if mode in ("System", "Dark", "Light") else "System"
        except Exception:  # noqa: BLE001
            return "System"

    def _save_appearance(self, mode: str) -> None:
        try:
            Path("launcher.state.json").write_text(
                json.dumps({"appearance": mode}), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001, S110
            pass

    def _apply_appearance(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)
        if hasattr(self, "appearance"):
            self.appearance.set(mode)

    def _on_appearance(self, choice: str) -> None:
        self._apply_appearance(choice)
        self._save_appearance(choice)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(
        self, screen_class: type[ctk.CTkFrame], *args: Any, **kwargs: Any
    ) -> None:
        def swap() -> None:
            if self.current_screen is not None:
                self.current_screen.destroy()
            _cls: Any = screen_class
            new_screen = _cls(self.content, self, *args, **kwargs)
            new_screen.grid(row=0, column=0, sticky="nsew")
            self.current_screen = new_screen
            # Capture the MainScreen reference here, inside swap(): with
            # animations on, swap() runs asynchronously (~180ms after
            # show_screen returns), so assigning _main_screen at the call
            # site would race and leave it stale/None -> _on_close would fail
            # to stop the server. Setting it here is correct on both paths.
            self._main_screen = (
                new_screen if isinstance(new_screen, MainScreen) else None
            )

        screen_transition(self.root, swap, reduced=self._reduced_motion)

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

    def _ensure_database(self) -> bool:
        """Ensure a valid, migrated arcade.db exists before the server starts.

        - Present DB -> ensure schema is current.
        - Missing DB  -> ask the user to restore the latest backup or create new.
        - Cancelled   -> quit the launcher (never boot a broken/absent DB).

        Returns ``True`` if the launcher should proceed to ``MainScreen``
        (a DB was ensured), or ``False`` if the user cancelled and the root
        was destroyed.
        """
        from backend.core import db_bootstrap
        from backend.core.config import load_config

        if db_bootstrap.is_db_present():
            db_bootstrap.ensure_schema_current()
            return True

        backup_dir = load_config().backup_dir
        latest = db_bootstrap.find_latest_backup(backup_dir)
        choice = self._ask_db_restore(latest)
        if choice == "restore" and latest is not None:
            try:
                db_bootstrap.restore_latest_backup(backup_dir)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(
                    "Restore failed",
                    f"Could not restore the backup:\n{exc}\n\n"
                    "A new empty database will be created instead.",
                )
                db_bootstrap.create_fresh_database()
        elif choice == "create":
            db_bootstrap.create_fresh_database()
        else:
            # User dismissed the dialog without choosing: do not start server.
            self.root.destroy()
            return False
        return True

    def _ask_db_restore(self, latest: Path | None) -> str:
        """Blocking modal: 'restore latest backup' / 'create new' / 'cancel'.

        Returns one of 'restore', 'create', or 'cancel'.
        """
        response: dict[str, str] = {"choice": "cancel"}
        f = self.fonts

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Database Not Found")
        dialog.geometry("520x340")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        _center_window(dialog, 520, 340)

        ctk.CTkLabel(
            dialog,
            text="No database found",
            font=f["h2"],
            text_color=COLORS["text_primary"],
        ).pack(padx=24, pady=(24, 6))
        ctk.CTkLabel(
            dialog,
            text=(
                "Arcade could not find arcade.db. Restore the most recent "
                "backup, or start with a new (empty) database."
            ),
            font=f["body"],
            text_color=COLORS["text_secondary"],
            wraplength=460,
            justify="left",
        ).pack(padx=24, pady=(0, 12))

        if latest is not None:
            ctk.CTkLabel(
                dialog,
                text=f"Latest backup: {latest.name}",
                font=f["mono"],
                text_color=COLORS["text_primary"],
            ).pack(padx=24, pady=(0, 12))

        def _choose(value: str) -> None:
            response["choice"] = value
            dialog.grab_release()
            dialog.destroy()

        restore_btn = ctk.CTkButton(
            dialog,
            text="Restore latest backup",
            command=lambda: _choose("restore"),
            state="normal" if latest is not None else "disabled",
            font=f["body_bold"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["accent_fill"],
            hover_color=COLORS["accent_fill_hover"],
            text_color=COLORS["text_on_accent"],
        )
        restore_btn.pack(fill="x", padx=24, pady=(4, 10))
        create_btn = ctk.CTkButton(
            dialog,
            text="Create new database",
            command=lambda: _choose("create"),
            font=f["body_bold"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["success_fill"],
            hover_color=COLORS["success_fill"][1],
            text_color=COLORS["text_on_accent"],
        )
        create_btn.pack(fill="x", padx=24, pady=(0, 10))
        cancel_btn = ctk.CTkButton(
            dialog,
            text="Cancel",
            command=lambda: _choose("cancel"),
            font=f["body"],
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        cancel_btn.pack(fill="x", padx=24, pady=(0, 16))

        dialog.protocol("WM_DELETE_WINDOW", lambda: _choose("cancel"))
        self.root.wait_window(dialog)
        return response["choice"]

    # ------------------------------------------------------------------
    # License routing (FR-SYS-008)
    # ------------------------------------------------------------------

    def _check_and_route(self) -> None:
        result = check_license()
        if result.ok:
            if Path("arcade.config.json").exists():
                if self._ensure_database():
                    # _main_screen is captured inside show_screen's swap(),
                    # which runs after the screen is built (async when
                    # animations are on).
                    self.show_screen(MainScreen)
                    self.status.set("Database ready", "success")
            else:
                self.show_screen(SetupWizard, result)
                self.status.set("Setup required", "busy")
        else:
            self.show_screen(ActivationScreen, result)
            self.status.set("License required", "error")

    # ------------------------------------------------------------------
    # Entry hook
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()


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
