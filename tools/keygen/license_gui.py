"""Graphical interface for the Arcade offline license generator.

INTERNAL USE ONLY. Lets a provider fill in a form (hardware ID, cafe name,
license type, optional trial days, output path) and produce a signed
``license.key`` without touching the command line.

``launch_gui()`` is imported lazily by ``generate_license.main()`` so the CLI
path never imports customtkinter. The cryptographic path in
``generate_license`` is untouched by this module.

Visual design follows the Arcade brand: slate surfaces, brand-blue primary
action, success/danger accents, a branded header with the Arcade logo, a real
type scale, an 8px spacing rhythm, a custom success toast, and WCAG-AA
dark/light themes.
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
    from .license_helpers import resolve_logo_path, validate_inputs
except ImportError:  # direct `python license_gui.py` run: no parent package
    from generate_license import (
        KeygenError,
        build_and_write_license,
        format_verify_command,
        parse_trial_days,
    )
    from license_helpers import resolve_logo_path, validate_inputs

# Brand palette (mirrors frontend/src/index.css) as (light, dark) tuples.
_BRAND = {
    "title": ("#0F172A", "#F8FAFC"),
    "label": ("#334155", "#CBD5E1"),
    "muted": ("#64748B", "#94A3B8"),
    "required": ("#DC2626", "#F87171"),
    "card": ("#FFFFFF", "#1E293B"),
    "card_border": ("#E2E8F0", "#334155"),
    "header_bg": ("#FFFFFF", "#1E293B"),
    "primary": ("#2563EB", "#3B82F6"),
    "primary_hover": ("#1D4ED8", "#2563EB"),
    "primary_text": ("#FFFFFF", "#0F172A"),
    "secondary": ("gray90", "#334155"),
    "secondary_hover": ("gray85", "#475569"),
    "secondary_border": ("#CBD5E1", "#475569"),
    "secondary_text": ("#0F172A", "#F8FAFC"),
    "success": ("#16A34A", "#4ADE80"),
    "error": ("#DC2626", "#F87171"),
    "error_border": ("#DC2626", "#F87171"),
}

PAD = 8  # base spacing unit (8px rhythm)


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
    """Builds the CustomTkinter form and wires callbacks."""

    def __init__(self, ctk) -> None:
        self.ctk = ctk
        self.root = ctk.CTk()
        self.root.title("Arcade License Generator")
        self.root.geometry("620x760")
        self.root.minsize(560, 680)
        self.root.resizable(True, True)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.root.grid_columnconfigure(0, weight=1)

        self._last_blob = ""
        self._last_verify = ""
        self._toast_after = None
        self._build_header()
        self._build_scroll()
        self._build_form()
        self._build_actions()
        self._build_result()

    # -- header ----------------------------------------------------------
    def _build_header(self) -> None:
        ctk = self.ctk
        header = ctk.CTkFrame(self.root, fg_color=_BRAND["header_bg"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        logo_path = resolve_logo_path()
        if logo_path:
            try:
                from PIL import Image

                pil = Image.open(logo_path)
                self.logo_img = ctk.CTkImage(
                    light_image=pil, dark_image=pil, size=(64, 64)
                )
                ctk.CTkLabel(header, image=self.logo_img, text="").grid(
                    row=0, column=0, rowspan=2, padx=(24, 16), pady=(20, 8)
                )
            except Exception:
                self.logo_img = None
        else:
            self.logo_img = None

        ctk.CTkLabel(
            header,
            text="Arcade",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=_BRAND["title"],
        ).grid(row=0, column=1, sticky="w", padx=(0, 0), pady=(20, 0))
        ctk.CTkLabel(
            header,
            text="License Generator",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=_BRAND["muted"],
        ).grid(row=1, column=1, sticky="w", pady=(0, 4))

        self.appearance_option = ctk.CTkOptionMenu(
            header,
            values=["System", "Dark", "Light"],
            width=110,
            command=self._on_appearance_change,
        )
        self.appearance_option.set("System")
        self.appearance_option.grid(
            row=0, column=2, rowspan=2, sticky="e", padx=(0, 24), pady=(20, 8)
        )

        grad = self._gradient_strip()
        if grad is not None:
            ctk.CTkLabel(header, image=grad, text="").grid(
                row=2, column=0, columnspan=3, sticky="ew", pady=(0, 0)
            )

        ctk.CTkLabel(
            header,
            text="Issue a signed license key for a cafe machine.  Internal tool.",
            font=ctk.CTkFont(size=12),
            text_color=_BRAND["muted"],
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=24, pady=(0, 16))

    def _gradient_strip(self):
        ctk = self.ctk
        gpath = Path(__file__).resolve().parent / "icon" / "arcade_gradient_3px.png"
        if not gpath.exists():
            return None
        try:
            from PIL import Image

            img = Image.open(gpath)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(600, 3))
        except Exception:
            return None

    # -- scroll container ------------------------------------------------
    def _build_scroll(self) -> None:
        ctk = self.ctk
        self.scroll = ctk.CTkScrollableFrame(
            self.root, fg_color="transparent", corner_radius=0
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

    # -- form ------------------------------------------------------------
    def _build_form(self) -> None:
        ctk = self.ctk
        card = ctk.CTkFrame(
            self.scroll,
            fg_color=_BRAND["card"],
            border_width=1,
            border_color=_BRAND["card_border"],
            corner_radius=12,
        )
        card.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        card.grid_columnconfigure(0, weight=1)

        self._section_label(card, "License details")

        row = self._field_label(card, 1, "Hardware ID", required=True)
        self.hwid_entry = ctk.CTkEntry(
            card,
            placeholder_text="e.g. a1b2c3... (from get_hardware_id())",
            height=40,
        )
        self.hwid_entry.grid(row=row, column=0, sticky="ew", padx=24, pady=(6, 0))
        self.hwid_error = self._error_label(card, row + 1)
        self.hwid_entry.bind("<KeyRelease>", lambda e: self._clear_error("hwid_entry"))
        row += 2

        ctk.CTkLabel(
            card,
            text="The target machine's hardware ID. Run get_hardware_id() on that PC.",
            font=ctk.CTkFont(size=11),
            text_color=_BRAND["muted"],
        ).grid(row=row, column=0, sticky="w", padx=24, pady=(2, 0))
        row += 1

        row = self._field_label(card, row, "Cafe Name", required=True)
        self.cafe_entry = ctk.CTkEntry(
            card, placeholder_text="Galaxy Gaming Lounge", height=40
        )
        self.cafe_entry.grid(row=row, column=0, sticky="ew", padx=24, pady=(6, 0))
        self.cafe_error = self._error_label(card, row + 1)
        self.cafe_entry.bind("<KeyRelease>", lambda e: self._clear_error("cafe_entry"))
        row += 2

        row = self._field_label(card, row, "License Type")
        self.type_option = ctk.CTkOptionMenu(
            card,
            values=["PERPETUAL", "TRIAL"],
            height=40,
            command=self._on_type_change,
        )
        self.type_option.set("PERPETUAL")
        self.type_option.grid(row=row, column=0, sticky="ew", padx=24, pady=(6, 0))
        row += 1

        row = self._field_label(card, row, "Trial Days")
        self.trial_entry = ctk.CTkEntry(
            card, placeholder_text="30", height=40, state="disabled"
        )
        self.trial_entry.grid(row=row, column=0, sticky="ew", padx=24, pady=(6, 0))
        self.trial_error = self._error_label(card, row + 1)
        row += 2
        ctk.CTkLabel(
            card,
            text="Only used for TRIAL licenses. Leave blank for PERPETUAL.",
            font=ctk.CTkFont(size=11),
            text_color=_BRAND["muted"],
        ).grid(row=row, column=0, sticky="w", padx=24, pady=(2, 16))

        row += 1
        row = self._field_label(card, row, "Output File")
        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(row=row, column=0, sticky="ew", padx=24, pady=(6, 16))
        path_row.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(
            path_row, placeholder_text="license.key", height=40
        )
        self.path_entry.insert(0, "license.key")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            path_row, text="Browse", width=96, height=40, command=self._browse
        ).grid(row=0, column=1)

    # -- actions & status ------------------------------------------------
    def _build_actions(self) -> None:
        ctk = self.ctk
        self.generate_btn = ctk.CTkButton(
            self.scroll,
            text="Generate License",
            height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=_BRAND["primary"],
            hover_color=_BRAND["primary_hover"],
            text_color=_BRAND["primary_text"],
            command=self._on_generate,
        )
        self.generate_btn.grid(row=1, column=0, sticky="ew", padx=24, pady=(20, 0))

        self.status_label = ctk.CTkLabel(
            self.scroll,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_BRAND["muted"],
        )
        self.status_label.grid(row=2, column=0, sticky="w", padx=24, pady=(12, 0))

        self._build_toast()

    def _build_toast(self) -> None:
        ctk = self.ctk
        self.toast = ctk.CTkFrame(
            self.scroll,
            fg_color=_BRAND["card"],
            border_width=1,
            border_color=_BRAND["success"],
            corner_radius=10,
        )
        self.toast.grid(row=3, column=0, sticky="e", padx=24, pady=(8, 0))
        self.toast.grid_remove()  # hidden until first success
        badge = ctk.CTkLabel(
            self.toast,
            text="✓",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=_BRAND["success"],
            width=24,
        )
        badge.grid(row=0, column=0, padx=(12, 8), pady=10)
        self.toast_msg = ctk.CTkLabel(
            self.toast,
            text="License generated",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=_BRAND["title"],
        )
        self.toast_msg.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="w")

    # -- result ----------------------------------------------------------
    def _build_result(self) -> None:
        ctk = self.ctk
        self.result_card = ctk.CTkFrame(
            self.scroll,
            fg_color=_BRAND["card"],
            border_width=1,
            border_color=_BRAND["card_border"],
            corner_radius=12,
        )
        self.result_card.grid(row=4, column=0, sticky="ew", padx=24, pady=(16, 24))
        self.result_card.grid_columnconfigure(0, weight=1)
        self.result_card.grid_remove()  # shown on first successful generate

        self._section_label(self.result_card, "Result")
        self.result_box = ctk.CTkTextbox(
            self.result_card,
            height=130,
            state="disabled",
            font=ctk.CTkFont(family="Courier New", size=11),
        )
        self.result_box.grid(row=1, column=0, sticky="ew", padx=24, pady=(8, 12))

        copy_row = ctk.CTkFrame(self.result_card, fg_color="transparent")
        copy_row.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 20))
        copy_row.grid_columnconfigure(0, weight=1)
        copy_row.grid_columnconfigure(1, weight=1)
        self.copy_license_btn = ctk.CTkButton(
            copy_row,
            text="Copy License String",
            height=38,
            fg_color=_BRAND["secondary"],
            hover_color=_BRAND["secondary_hover"],
            text_color=_BRAND["secondary_text"],
            border_width=1,
            border_color=_BRAND["secondary_border"],
            command=lambda: self._copy(
                self._last_blob or "", self.copy_license_btn, "Copy License String"
            ),
        )
        self.copy_license_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.copy_verify_btn = ctk.CTkButton(
            copy_row,
            text="Copy Verify Command",
            height=38,
            fg_color=_BRAND["secondary"],
            hover_color=_BRAND["secondary_hover"],
            text_color=_BRAND["secondary_text"],
            border_width=1,
            border_color=_BRAND["secondary_border"],
            command=lambda: self._copy(
                self._last_verify or "", self.copy_verify_btn, "Copy Verify Command"
            ),
        )
        self.copy_verify_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    # -- shared widgets --------------------------------------------------
    def _section_label(self, parent, text: str) -> None:
        ctk = self.ctk
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=_BRAND["title"],
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 8))

    def _field_label(self, parent, row: int, name: str, required: bool = False) -> int:
        ctk = self.ctk
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="w", padx=24, pady=(16, 0))
        ctk.CTkLabel(
            frame,
            text=name,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=_BRAND["label"],
        ).grid(row=0, column=0, sticky="w")
        if required:
            ctk.CTkLabel(
                frame,
                text="*",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=_BRAND["required"],
            ).grid(row=0, column=1, sticky="w", padx=(3, 0))
        return row + 1

    def _error_label(self, parent, row: int):
        ctk = self.ctk
        lbl = ctk.CTkLabel(
            parent,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_BRAND["error"],
        )
        lbl.grid(row=row, column=0, sticky="w", padx=24, pady=(2, 0))
        lbl.grid_remove()
        return lbl

    # -- callbacks -------------------------------------------------------
    def _on_appearance_change(self, choice: str) -> None:
        self.ctk.set_appearance_mode(choice)

    def _on_type_change(self, choice: str) -> None:
        state = "normal" if choice == "TRIAL" else "disabled"
        self.trial_entry.configure(state=state)
        if choice != "TRIAL":
            self._clear_error("trial_entry")

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

    def _set_field_error(
        self, field: str, widget, error_label, message: str, first_invalid
    ) -> None:
        widget.configure(border_color=_BRAND["error_border"])
        error_label.configure(text=message)
        error_label.grid()  # reveal
        if first_invalid[0] is None:
            first_invalid[0] = widget

    def _clear_error(self, field: str) -> None:
        # Map field name -> (entry widget, error label) explicitly.
        mapping = {
            "hwid_entry": (self.hwid_entry, self.hwid_error),
            "cafe_entry": (self.cafe_entry, self.cafe_error),
            "trial_entry": (self.trial_entry, self.trial_error),
        }
        pair = mapping.get(field)
        if pair is None:
            return
        widget, err = pair
        err.grid_remove()
        widget.configure(border_color=_BRAND["card_border"])

    def _show_toast(self, message: str) -> None:
        self.toast_msg.configure(text=message)
        self.toast.grid()  # reveal
        if self._toast_after:
            self.root.after_cancel(self._toast_after)
        self._toast_after = self.root.after(2600, self.toast.grid_remove)

    def _copy(self, text: str, btn, original: str) -> None:
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        btn.configure(text="Copied ✓")
        self.root.after(1200, lambda: btn.configure(text=original))

    def _on_generate(self) -> None:
        hardware_id = self.hwid_entry.get().strip()
        cafe_name = self.cafe_entry.get().strip()
        license_type = self.type_option.get()
        output_path = self.path_entry.get().strip() or "license.key"

        # Reset prior error visuals.
        for f in ("hwid_entry", "cafe_entry", "trial_entry"):
            self._clear_error(f)

        errors = validate_inputs(
            hardware_id, cafe_name, license_type, self.trial_entry.get()
        )
        first_invalid = [None]
        if "hardware_id" in errors:
            self._set_field_error(
                "hwid_entry",
                self.hwid_entry,
                self.hwid_error,
                errors["hardware_id"],
                first_invalid,
            )
        if "cafe_name" in errors:
            self._set_field_error(
                "cafe_entry",
                self.cafe_entry,
                self.cafe_error,
                errors["cafe_name"],
                first_invalid,
            )
        if "trial_days" in errors:
            self._set_field_error(
                "trial_entry",
                self.trial_entry,
                self.trial_error,
                errors["trial_days"],
                first_invalid,
            )
        if errors:
            self._set_status("Please fix the highlighted fields.", ok=False)
            if first_invalid[0] is not None:
                first_invalid[0].focus_set()
            return

        try:
            trial_days = (
                parse_trial_days(self.trial_entry.get())
                if license_type == "TRIAL"
                else None
            )
        except ValueError:
            self._set_field_error(
                "trial_entry",
                self.trial_entry,
                self.trial_error,
                "Trial Days must be a positive number.",
                first_invalid,
            )
            self._set_status("Trial Days must be a positive number.", ok=False)
            return

        self.generate_btn.configure(state="disabled", text="Generating…")
        try:
            blob = build_and_write_license(
                hardware_id=hardware_id,
                cafe_name=cafe_name,
                license_type=license_type,
                trial_days=trial_days,
                output_path=output_path,
            )
        except KeygenError as exc:
            self.generate_btn.configure(state="normal", text="Generate License")
            self._set_status(str(exc), ok=False)
            messagebox.showerror("License generation failed", str(exc))
            return

        self.generate_btn.configure(state="normal", text="Generate License")
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
        self.result_card.grid()  # reveal on first success
        self._show_toast("License generated")
        self._set_status("License generated successfully.", ok=True)

    # -- run -------------------------------------------------------------
    def run(self) -> None:
        self.root.mainloop()


def launch_gui() -> None:
    """Entry point used by ``generate_license.main()``. Lazy-imports customtkinter."""
    ctk = _require_customtkinter()
    LicenseApp(ctk).run()
