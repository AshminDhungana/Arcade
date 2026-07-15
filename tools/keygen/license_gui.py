"""Graphical interface for the Arcade offline license generator.

INTERNAL USE ONLY. Lets a provider fill in a form (hardware ID, cafe name,
license type, optional trial days, output path) and produce a signed
``license.key`` without touching the command line.

``launch_gui()`` is imported lazily by ``generate_license.main()`` so the CLI
path never imports customtkinter.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

from .generate_license import (
    KeygenError,
    build_and_write_license,
    format_verify_command,
    parse_trial_days,
)


def _require_customtkinter():
    try:
        import customtkinter as ctk
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "customtkinter is required for the GUI. "
            "Install with: pip install -r tools/keygen/requirements.txt"
        ) from exc
    return ctk


class LicenseApp:
    """Thin wrapper that builds the CustomTkinter form and wires callbacks."""

    def __init__(self, ctk) -> None:
        self.ctk = ctk
        self.root = ctk.CTk()
        self.root.title("Arcade License Generator")
        self.root.geometry("560x620")
        self.root.resizable(False, False)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self._build()

    # -- layout -----------------------------------------------------------
    def _build(self) -> None:
        ctk = self.ctk
        pad = {"padx": 20, "pady": (10, 0)}

        ctk.CTkLabel(
            self.root,
            text="Arcade License Generator",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", **pad)

        # Theme toggle (Light / Dark / System) — "look good" control.
        self.appearance_option = ctk.CTkOptionMenu(
            self.root,
            values=["System", "Dark", "Light"],
            width=110,
            command=self._on_appearance_change,
        )
        self.appearance_option.set("System")
        self.appearance_option.grid(row=0, column=1, sticky="e", padx=20, pady=(10, 0))

        ctk.CTkLabel(
            self.root,
            text="Fill in the target machine details, then Generate.",
            text_color=("gray40", "gray60"),
        ).grid(row=1, column=0, sticky="w", **pad)

        # Hardware ID
        ctk.CTkLabel(self.root, text="Hardware ID").grid(
            row=2, column=0, sticky="w", **pad
        )
        self.hwid_entry = ctk.CTkEntry(
            self.root, placeholder_text="e.g. a1b2c3... (from get_hardware_id())"
        )
        self.hwid_entry.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 0))

        # Cafe name
        ctk.CTkLabel(self.root, text="Cafe Name").grid(
            row=4, column=0, sticky="w", **pad
        )
        self.cafe_entry = ctk.CTkEntry(
            self.root, placeholder_text="Galaxy Gaming Lounge"
        )
        self.cafe_entry.grid(row=5, column=0, sticky="ew", padx=20, pady=(4, 0))

        # License type + trial days (side by side)
        ctk.CTkLabel(self.root, text="License Type").grid(
            row=6, column=0, sticky="w", **pad
        )
        self.type_option = ctk.CTkOptionMenu(
            self.root, values=["PERPETUAL", "TRIAL"], command=self._on_type_change
        )
        self.type_option.set("PERPETUAL")
        self.type_option.grid(row=7, column=0, sticky="ew", padx=20, pady=(4, 0))

        ctk.CTkLabel(self.root, text="Trial Days (if TRIAL)").grid(
            row=8, column=0, sticky="w", **pad
        )
        self.trial_entry = ctk.CTkEntry(
            self.root, placeholder_text="30", state="disabled"
        )
        self.trial_entry.grid(row=9, column=0, sticky="ew", padx=20, pady=(4, 0))

        # Output path
        ctk.CTkLabel(self.root, text="Output File").grid(
            row=10, column=0, sticky="w", **pad
        )
        path_row = ctk.CTkFrame(self.root, fg_color="transparent")
        path_row.grid(row=11, column=0, sticky="ew", padx=20, pady=(4, 0))
        path_row.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(path_row, placeholder_text="license.key")
        self.path_entry.insert(0, "license.key")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(path_row, text="Browse", width=90, command=self._browse).grid(
            row=0, column=1
        )

        # Generate button
        ctk.CTkButton(
            self.root,
            text="Generate License",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_generate,
        ).grid(row=12, column=0, sticky="ew", padx=20, pady=16)

        # Status line
        self.status_label = ctk.CTkLabel(self.root, text="", text_color="gray50")
        self.status_label.grid(row=13, column=0, sticky="w", padx=20)

        # Result box + copy
        self.result_box = ctk.CTkTextbox(self.root, height=120, state="disabled")
        self.result_box.grid(row=14, column=0, sticky="ew", padx=20, pady=(4, 0))
        ctk.CTkButton(
            self.root,
            text="Copy License String",
            width=180,
            command=lambda: self._copy(self._last_blob or ""),
        ).grid(row=15, column=0, sticky="w", padx=20, pady=(8, 0))
        ctk.CTkButton(
            self.root,
            text="Copy Verify Command",
            width=180,
            command=lambda: self._copy(self._last_verify or ""),
        ).grid(row=16, column=0, sticky="w", padx=20, pady=(4, 0))

        self._last_blob = ""
        self._last_verify = ""

    # -- callbacks --------------------------------------------------------
    def _on_appearance_change(self, choice: str) -> None:
        self.ctk.set_appearance_mode(choice)

    def _on_type_change(self, choice: str) -> None:
        state = "normal" if choice == "TRIAL" else "disabled"
        self.trial_entry.configure(state=state)

    def _browse(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".key",
            filetypes=[("License key", "*.key"), ("All files", "*.*")],
            initialfile=self.path_entry.get() or "license.key",
        )
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

    def _set_status(self, text: str, ok: bool) -> None:
        color = ("#2e7d32", "#3ddc84") if ok else ("#c62828", "#ff6b6b")
        self.status_label.configure(text=text, text_color=color)

    def _copy(self, text: str) -> None:
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # ensure clipboard is set before any dialog
        self._set_status("Copied to clipboard.", ok=True)

    def _on_generate(self) -> None:
        hardware_id = self.hwid_entry.get().strip()
        cafe_name = self.cafe_entry.get().strip()
        license_type = self.type_option.get()
        output_path = self.path_entry.get().strip() or "license.key"

        if not hardware_id or not cafe_name:
            self._set_status("Hardware ID and Cafe Name are required.", ok=False)
            return

        try:
            trial_days = (
                parse_trial_days(self.trial_entry.get())
                if license_type == "TRIAL"
                else None
            )
        except ValueError:
            self._set_status("Trial Days must be a positive number.", ok=False)
            return

        try:
            blob = build_and_write_license(
                hardware_id=hardware_id,
                cafe_name=cafe_name,
                license_type=license_type,
                trial_days=trial_days,
                output_path=output_path,
            )
        except KeygenError as exc:
            self._set_status(str(exc), ok=False)
            messagebox.showerror("License generation failed", str(exc))
            return

        self._last_blob = blob
        self._last_verify = format_verify_command(output_path)
        self.result_box.configure(state="normal")
        self.result_box.delete("0.0", "end")
        self.result_box.insert(
            "0.0",
            f"License written to: {Path(output_path).resolve()}\n\n{blob}\n\n"
            f"Verify:\n{self._last_verify}",
        )
        self.result_box.configure(state="disabled")
        self._set_status("License generated successfully.", ok=True)

    # -- run --------------------------------------------------------------
    def run(self) -> None:
        self.root.mainloop()


def launch_gui() -> None:
    """Entry point used by ``generate_license.main()``. Lazy-imports customtkinter."""
    ctk = _require_customtkinter()
    LicenseApp(ctk).run()
