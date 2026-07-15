"""Graphical interface for the Arcade offline license generator.

INTERNAL USE ONLY. Lets a provider fill in a form (hardware ID, cafe name,
license type, optional trial days, output path) and produce a signed
``license.key`` without touching the command line.

``launch_gui()`` is imported lazily by ``generate_license.main()`` so the CLI
path never imports customtkinter.

Visual design follows the Arcade brand (see ``frontend/src/index.css``):
slate surfaces, brand-blue primary action, success/danger accents, and a
Minimal Single Column layout with an 8px spacing rhythm.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

try:
    from .generate_license import (
        KeygenError,
        build_and_write_license,
        format_verify_command,
        parse_trial_days,
    )
except ImportError:  # direct `python generate_license.py` run: no parent package
    from generate_license import (
        KeygenError,
        build_and_write_license,
        format_verify_command,
        parse_trial_days,
    )

# Brand palette (mirrors frontend/src/index.css) as (light, dark) tuples.
_BRAND = {
    "title": ("#0F172A", "#F8FAFC"),
    "label": ("#334155", "#CBD5E1"),
    "muted": ("#64748B", "#94A3B8"),
    "required": ("#DC2626", "#F87171"),
    "card": ("#FFFFFF", "#1E293B"),
    "card_border": ("#E2E8F0", "#334155"),
    "primary": ("#2563EB", "#3B82F6"),
    "primary_hover": ("#1D4ED8", "#2563EB"),
    "secondary": ("gray90", "#334155"),
    "secondary_hover": ("gray85", "#475569"),
    "secondary_border": ("#CBD5E1", "#475569"),
    "success": ("#16A34A", "#4ADE80"),
    "error": ("#DC2626", "#F87171"),
}


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
        self.root.geometry("560x700")
        self.root.minsize(520, 640)
        self.root.resizable(True, True)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self._build()

    # -- layout -----------------------------------------------------------
    def _build(self) -> None:
        ctk = self.ctk
        padx = 24

        # Header: title + appearance toggle.
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=padx, pady=(24, 0))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Arcade License Generator",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=_BRAND["title"],
        ).grid(row=0, column=0, sticky="w")
        self.appearance_option = ctk.CTkOptionMenu(
            header,
            values=["System", "Dark", "Light"],
            width=120,
            command=self._on_appearance_change,
        )
        self.appearance_option.set("System")
        self.appearance_option.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            self.root,
            text="Issue a signed license key for a cafe machine.",
            font=ctk.CTkFont(size=12),
            text_color=_BRAND["muted"],
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=padx, pady=(6, 0))

        # Form card.
        card = ctk.CTkFrame(
            self.root,
            fg_color=_BRAND["card"],
            border_width=1,
            border_color=_BRAND["card_border"],
            corner_radius=12,
        )
        card.grid(row=2, column=0, columnspan=2, sticky="ew", padx=padx, pady=(20, 0))
        card.grid_columnconfigure(0, weight=1)
        self._build_fields(card, padx)

        # Primary action.
        ctk.CTkButton(
            self.root,
            text="Generate License",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=_BRAND["primary"],
            hover_color=_BRAND["primary_hover"],
            text_color="white",
            command=self._on_generate,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=padx, pady=(20, 0))

        # Status line.
        self.status_label = ctk.CTkLabel(
            self.root,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_BRAND["muted"],
        )
        self.status_label.grid(
            row=4, column=0, columnspan=2, sticky="w", padx=padx, pady=(12, 0)
        )

        # Result box (monospace for the base64 blob).
        self.result_box = ctk.CTkTextbox(
            self.root,
            height=130,
            state="disabled",
            font=ctk.CTkFont(family="Courier New", size=11),
        )
        self.result_box.grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=padx, pady=(8, 0)
        )

        # Copy actions (secondary buttons, side by side).
        copy_row = ctk.CTkFrame(self.root, fg_color="transparent")
        copy_row.grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=padx, pady=(10, 24)
        )
        copy_row.grid_columnconfigure(0, weight=1)
        copy_row.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            copy_row,
            text="Copy License String",
            height=36,
            fg_color=_BRAND["secondary"],
            hover_color=_BRAND["secondary_hover"],
            text_color=_BRAND["title"],
            border_width=1,
            border_color=_BRAND["secondary_border"],
            command=lambda: self._copy(self._last_blob or ""),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            copy_row,
            text="Copy Verify Command",
            height=36,
            fg_color=_BRAND["secondary"],
            hover_color=_BRAND["secondary_hover"],
            text_color=_BRAND["title"],
            border_width=1,
            border_color=_BRAND["secondary_border"],
            command=lambda: self._copy(self._last_verify or ""),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self._last_blob = ""
        self._last_verify = ""

    def _build_fields(self, card, padx: int) -> None:
        """Build the labeled form fields inside the card frame."""
        ctk = self.ctk
        label_font = ctk.CTkFont(size=13, weight="bold")
        help_font = ctk.CTkFont(size=11)

        def field_label(row: int, name: str, required: bool = False) -> int:
            frame = ctk.CTkFrame(card, fg_color="transparent")
            frame.grid(row=row, column=0, sticky="w", padx=padx, pady=(16, 0))
            ctk.CTkLabel(
                frame, text=name, font=label_font, text_color=_BRAND["label"]
            ).grid(row=0, column=0, sticky="w")
            if required:
                ctk.CTkLabel(
                    frame, text="*", font=label_font, text_color=_BRAND["required"]
                ).grid(row=0, column=1, sticky="w", padx=(3, 0))
            return row + 1

        # Hardware ID
        row = field_label(0, "Hardware ID", required=True)
        self.hwid_entry = ctk.CTkEntry(
            card, placeholder_text="e.g. a1b2c3... (from get_hardware_id())", height=36
        )
        self.hwid_entry.grid(row=row, column=0, sticky="ew", padx=padx, pady=(6, 0))
        row += 1
        ctk.CTkLabel(
            card,
            text="The target machine's hardware ID. Run get_hardware_id() on that PC.",
            font=help_font,
            text_color=_BRAND["muted"],
        ).grid(row=row, column=0, sticky="w", padx=padx, pady=(4, 0))
        row += 1

        # Cafe Name
        row = field_label(row, "Cafe Name", required=True)
        self.cafe_entry = ctk.CTkEntry(
            card, placeholder_text="Galaxy Gaming Lounge", height=36
        )
        self.cafe_entry.grid(row=row, column=0, sticky="ew", padx=padx, pady=(6, 0))
        row += 1

        # License Type
        row = field_label(row, "License Type")
        self.type_option = ctk.CTkOptionMenu(
            card, values=["PERPETUAL", "TRIAL"], command=self._on_type_change, height=36
        )
        self.type_option.set("PERPETUAL")
        self.type_option.grid(row=row, column=0, sticky="ew", padx=padx, pady=(6, 0))
        row += 1

        # Trial Days
        row = field_label(row, "Trial Days")
        self.trial_entry = ctk.CTkEntry(
            card, placeholder_text="30", height=36, state="disabled"
        )
        self.trial_entry.grid(row=row, column=0, sticky="ew", padx=padx, pady=(6, 0))
        row += 1
        ctk.CTkLabel(
            card,
            text="Only used for TRIAL licenses. Leave blank for PERPETUAL.",
            font=help_font,
            text_color=_BRAND["muted"],
        ).grid(row=row, column=0, sticky="w", padx=padx, pady=(4, 0))
        row += 1

        # Output File
        row = field_label(row, "Output File")
        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(row=row, column=0, sticky="ew", padx=padx, pady=(6, 0))
        path_row.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(
            path_row, placeholder_text="license.key", height=36
        )
        self.path_entry.insert(0, "license.key")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            path_row, text="Browse", width=90, height=36, command=self._browse
        ).grid(row=0, column=1)

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
        color = _BRAND["success"] if ok else _BRAND["error"]
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
