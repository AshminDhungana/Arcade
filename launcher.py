"""Arcade Launcher - Tkinter GUI for license activation and server management.

Entry point for the Arcade server. Checks the Ed25519 license before the
main window is shown, then routes to one of three screens:

* ActivationScreen — license missing/invalid/bound to another machine
* SetupWizard — license valid but arcade.config.json missing
* MainScreen — ready to start/stop the server
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
    BLUE,
    BLUE_HOVER,
    BTN_HEIGHT,
    EMERALD,
    EMERALD_HOVER,
    L_BG,
    L_BORDER,
    L_FRAME,
    L_TEXT,
    MUTED_TEXT,
    RADIUS,
    RED,
    RED_HOVER,
    S700,
    S700_HOVER,
    S800,
    S900,
    TEXT,
    body_font,
    brand_header,
    heading_font,
    mono_font,
)

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _center_window(root: ctk.CTk, width: int, height: int) -> None:
    """Center the window on the screen."""
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")


class _BaseScreen(ctk.CTkFrame):  # type: ignore[misc]
    """Base screen with common styling."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        controller: LauncherApp,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, fg_color=[L_BG, S900], **kwargs)
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
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        # Branded header
        header = brand_header(self, subtitle="License Activation Required")
        header.grid(row=0, column=0, padx=40, pady=(30, 10), sticky="ew")

        # Error box
        error = self.result.error or LicenseError.MISSING
        msg = _LICENSE_ERROR_MESSAGES.get(error, str(error))
        self.error_label = ctk.CTkLabel(
            self,
            text=msg,
            wraplength=560,
            justify="center",
            font=body_font(13),
            text_color=RED,
        )
        self.error_label.grid(row=1, column=0, padx=40, pady=(0, 20), sticky="ew")

        # Hardware ID section
        hwid_frame = ctk.CTkFrame(self, fg_color="transparent")
        hwid_frame.grid(row=2, column=0, padx=40, pady=(0, 10), sticky="ew")
        hwid_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hwid_frame,
            text="Hardware ID (give this to support):",
            font=heading_font(12),
            text_color=MUTED_TEXT,
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.hwid_var = tk.StringVar(value=get_hardware_id())
        hwid_entry = ctk.CTkEntry(
            hwid_frame,
            textvariable=self.hwid_var,
            state="readonly",
            font=mono_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=[L_FRAME, S800],
            border_color=[L_BORDER, S700],
            text_color=[L_TEXT, TEXT],
        )
        hwid_entry.grid(row=1, column=0, sticky="ew")

        # Copy button
        copy_btn = ctk.CTkButton(
            hwid_frame,
            text="Copy Hardware ID",
            command=self._copy_hwid,
            font=heading_font(12),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=[L_BORDER, S700],
            hover_color=[L_BORDER, S700_HOVER],
            text_color=[L_TEXT, TEXT],
        )
        copy_btn.grid(row=2, column=0, pady=(10, 0), sticky="ew")

        # Divider
        ctk.CTkFrame(self, height=1, fg_color=[L_BORDER, S700]).grid(
            row=3, column=0, padx=40, pady=20, sticky="ew"
        )

        # License key browse button
        ctk.CTkLabel(
            self,
            text="Have a license.key file?",
            font=heading_font(14),
            text_color=[L_TEXT, TEXT],
        ).grid(row=4, column=0, padx=40, pady=(0, 8))

        browse_btn = ctk.CTkButton(
            self,
            text="Browse for license.key …",
            command=self._browse,
            font=heading_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            text_color=TEXT,
        )
        browse_btn.grid(row=5, column=0, padx=40, pady=(0, 30), sticky="ew")

    def _copy_hwid(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.hwid_var.get())
        self.controller.root.bell()

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select license.key", filetypes=[("License files", "*.key")]
        )
        if path:
            dest = Path("license.key")
            try:
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
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # Header
        header = brand_header(self, subtitle="First-Time Setup")
        header.grid(row=0, column=0, padx=40, pady=(30, 10), sticky="ew")

        # Scrollable form area
        self.form = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self.form.grid(row=1, column=0, padx=40, pady=10, sticky="nsew")
        self.form.grid_columnconfigure(0, weight=1)

        row = 0

        # ── Café / Server ──
        self._section_header("Café & Server")
        row += 1

        self._cafe_name_var = ctk.StringVar()
        self._labeled_entry(
            "Café Name", self._cafe_name_var, placeholder="My Arcade", row=row
        )
        row += 1

        self._host_var = ctk.StringVar(value="0.0.0.0")
        self._labeled_entry("Server IP", self._host_var, placeholder="0.0.0.0", row=row)
        row += 1

        self._port_var = ctk.StringVar(value="8000")
        self._labeled_entry("Port", self._port_var, placeholder="8000", row=row)
        row += 1

        # Divider
        ctk.CTkFrame(self.form, height=1, fg_color=[L_BORDER, S700]).grid(
            row=row, column=0, sticky="ew", pady=16
        )
        row += 1

        # ── Staff ──
        self._section_header("Staff Accounts")
        row += 1

        ctk.CTkLabel(
            self.form,
            text="Create the default admin and cashier accounts. PINs are hashed.",
            font=body_font(11),
            text_color=MUTED_TEXT,
            wraplength=560,
            justify="left",
        ).grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        self._admin_id_var = ctk.StringVar(value="admin")
        self._labeled_entry("Admin Staff ID", self._admin_id_var, row=row)
        row += 1

        self._admin_pin_var = ctk.StringVar()
        self._labeled_entry(
            "Admin PIN",
            self._admin_pin_var,
            show="●",
            row=row,
            placeholder="4–6 digits",
        )
        row += 1

        self._cashier_id_var = ctk.StringVar(value="cashier")
        self._labeled_entry("Cashier Staff ID", self._cashier_id_var, row=row)
        row += 1

        self._cashier_pin_var = ctk.StringVar()
        self._labeled_entry(
            "Cashier PIN",
            self._cashier_pin_var,
            show="●",
            row=row,
            placeholder="4–6 digits",
        )
        row += 1

        # Divider
        ctk.CTkFrame(self.form, height=1, fg_color=[L_BORDER, S700]).grid(
            row=row, column=0, sticky="ew", pady=16
        )
        row += 1

        # ── Seats ──
        self._section_header("Seats")
        row += 1

        ctk.CTkLabel(
            self.form,
            text="Each seat gets a unique agent secret for secure WebSocket auth.",
            font=body_font(11),
            text_color=MUTED_TEXT,
            wraplength=560,
            justify="left",
        ).grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        self._seat_count_var = ctk.StringVar(value="8")
        self._labeled_entry("Number of Seats", self._seat_count_var, row=row)
        row += 1

        # Finish button (primary CTA)
        finish_btn = ctk.CTkButton(
            self,
            text="Finish Setup",
            command=self._finish,
            font=heading_font(14),
            height=BTN_HEIGHT + 4,
            corner_radius=RADIUS,
            fg_color=EMERALD,
            hover_color=EMERALD_HOVER,
            text_color=TEXT,
        )
        finish_btn.grid(row=2, column=0, padx=40, pady=(10, 30), sticky="ew")

    def _section_header(self, text: str) -> None:
        ctk.CTkLabel(
            self.form,
            text=text,
            font=heading_font(14),
            text_color=[L_TEXT, TEXT],
        ).grid(row=self.form.grid_size()[1], column=0, sticky="w", pady=(0, 8))

    def _labeled_entry(
        self,
        label: str,
        var: ctk.StringVar,
        *,
        show: str = "",
        row: int | None = None,
        placeholder: str = "",
    ) -> None:
        r = row if row is not None else self.form.grid_size()[1]
        ctk.CTkLabel(
            self.form, text=label, font=body_font(12), text_color=[L_TEXT, TEXT]
        ).grid(row=r, column=0, sticky="w", pady=(0, 4))
        entry = ctk.CTkEntry(
            self.form,
            textvariable=var,
            show=show,
            font=body_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=[L_FRAME, S800],
            border_color=[L_BORDER, S700],
            text_color=[L_TEXT, TEXT],
            placeholder_text=placeholder,
        )
        entry.grid(row=r + 1, column=0, sticky="ew", pady=(0, 12))

    def _seed_default_staff(self) -> None:
        """Best-effort: create the default admin + cashier in the DB."""
        import threading

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
        payload = self.license_result.payload or {}

        try:
            seat_count = int(self._seat_count_var.get())
        except ValueError:
            seat_count = 8

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
        self._stop_event = threading.Event()
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=0)

        # Header
        header = brand_header(self, subtitle="Server Control")
        header.grid(row=0, column=0, padx=40, pady=(30, 10), sticky="ew")

        # Status row
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=1, column=0, padx=40, pady=(0, 10), sticky="ew")
        status_frame.grid_columnconfigure(1, weight=1)

        self._dot = ctk.CTkCanvas(
            status_frame, width=16, height=16, bg=L_BG, highlightthickness=0
        )
        self._dot.grid(row=0, column=0, padx=(0, 12))
        self._dot_id = self._dot.create_oval(2, 2, 14, 14, fill=RED, outline="")

        self._status_var = ctk.StringVar(value="Stopped")
        ctk.CTkLabel(
            status_frame,
            textvariable=self._status_var,
            font=heading_font(14),
            text_color=[L_TEXT, TEXT],
        ).grid(row=0, column=1, sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=40, pady=(0, 10), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self._start_btn = ctk.CTkButton(
            btn_frame,
            text="Start Server",
            command=self._start_server,
            font=heading_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=EMERALD,
            hover_color=EMERALD_HOVER,
            text_color=TEXT,
        )
        self._start_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._stop_btn = ctk.CTkButton(
            btn_frame,
            text="Stop Server",
            command=self._stop_server,
            font=heading_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=RED,
            hover_color=RED_HOVER,
            text_color=TEXT,
            state="disabled",
        )
        self._stop_btn.grid(row=0, column=1, padx=6, sticky="ew")

        self._dashboard_btn = ctk.CTkButton(
            btn_frame,
            text="Open Dashboard",
            command=self._open_dashboard,
            font=heading_font(13),
            height=BTN_HEIGHT,
            corner_radius=RADIUS,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            text_color=TEXT,
        )
        self._dashboard_btn.grid(row=0, column=2, padx=(6, 0), sticky="ew")

        # Logs header
        log_header = ctk.CTkFrame(self, fg_color="transparent")
        log_header.grid(row=3, column=0, padx=40, pady=(10, 4), sticky="ew")
        log_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_header,
            text="Server Logs",
            font=heading_font(13),
            text_color=[L_TEXT, TEXT],
        ).grid(row=0, column=0, sticky="w")

        # Log area
        log_frame = ctk.CTkFrame(self, fg_color=[L_FRAME, S800], corner_radius=RADIUS)
        log_frame.grid(row=3, column=0, padx=40, pady=(0, 30), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self._log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg=L_FRAME,
            fg=L_TEXT,
            bd=0,
            highlightthickness=0,
        )
        self._log_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

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
        self._dot.itemconfig(self._dot_id, fill=EMERALD)
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")

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
        self._dot.itemconfig(self._dot_id, fill=RED)
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

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
# Root controller
# ---------------------------------------------------------------------------


class LauncherApp:
    """CustomTkinter application root. Manages screen switching."""

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("Arcade Launcher")
        self.root.geometry("720x600")
        self.root.minsize(720, 600)
        self.root.configure(fg_color=[L_BG, S900])
        self.current_screen: ctk.CTkFrame | None = None
        self._main_screen: MainScreen | None = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        _center_window(self.root, 720, 600)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(
        self, screen_class: type[ctk.CTkFrame], *args: Any, **kwargs: Any
    ) -> None:
        if self.current_screen is not None:
            self.current_screen.destroy()
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
                self._main_screen = self.current_screen
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
