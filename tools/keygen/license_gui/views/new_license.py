from __future__ import annotations

import base64
import json
import threading
from datetime import date

try:
    from ...generate_license import (
        build_and_write_license,
        format_verify_command,
        parse_trial_days,
    )
    from ...license_helpers import validate_inputs
    from ..theme import COLORS, RADIUS, SPACING
    from ..widgets import Card, LabeledField, ResultPanel, SegmentedControl, show_toast
except ImportError:
    from generate_license import (
        build_and_write_license,
        format_verify_command,
        parse_trial_days,
    )
    from license_helpers import validate_inputs

    from ..theme import COLORS, RADIUS, SPACING
    from ..widgets import Card, LabeledField, ResultPanel, SegmentedControl, show_toast


class NewLicenseView:
    def __init__(self, app, master) -> None:
        self.app = app
        self.ctk = app.ctk
        self.fonts = app.fonts

        self.frame = self.ctk.CTkScrollableFrame(master, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)

        card = Card(self.frame, self.ctk)
        card.grid(
            row=0, column=0, sticky="ew", padx=SPACING["xl"], pady=(SPACING["xl"], 0)
        )

        self.ctk.CTkLabel(
            card,
            text="License details",
            font=self.fonts["h2"],
            text_color=COLORS["text_primary"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        self.hwid = LabeledField(
            card,
            self.ctk,
            self.fonts,
            "Hardware ID",
            required=True,
            placeholder="e.g. a1b2c3... (from get_hardware_id())",
        )
        self.hwid.grid(row=1, column=0, sticky="ew", padx=SPACING["lg"])
        self.ctk.CTkLabel(
            card,
            text="The target machine's hardware ID. Run get_hardware_id() on that PC.",
            font=self.fonts["caption"],
            text_color=COLORS["text_secondary"],
        ).grid(row=2, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["xs"], 0))

        self.cafe = LabeledField(
            card,
            self.ctk,
            self.fonts,
            "Cafe Name",
            required=True,
            placeholder="Galaxy Gaming Lounge",
        )
        self.cafe.grid(
            row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["md"], 0)
        )

        self.ctk.CTkLabel(
            card,
            text="License Type",
            font=self.fonts["body_bold"],
            text_color=COLORS["text_primary"],
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["md"], SPACING["xs"]),
        )
        self.type = SegmentedControl(
            card,
            self.ctk,
            self.fonts,
            ["PERPETUAL", "TRIAL"],
            "PERPETUAL",
            self._on_type,
        )
        self.type.grid(row=5, column=0, sticky="ew", padx=SPACING["lg"])

        self.trial = LabeledField(
            card, self.ctk, self.fonts, "Trial Days", placeholder="30"
        )
        self.trial.grid(
            row=6, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["md"], 0)
        )
        self.trial.set_state("disabled")
        self.ctk.CTkLabel(
            card,
            text="Only used for TRIAL licenses. Leave blank for PERPETUAL.",
            font=self.fonts["caption"],
            text_color=COLORS["text_secondary"],
        ).grid(row=7, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["xs"], 0))

        self.ctk.CTkLabel(
            card,
            text="Output File",
            font=self.fonts["body_bold"],
            text_color=COLORS["text_primary"],
        ).grid(
            row=8,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["md"], SPACING["xs"]),
        )
        path_row = self.ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(
            row=9, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["lg"])
        )
        path_row.grid_columnconfigure(0, weight=1)
        self.path = self.ctk.CTkEntry(
            path_row,
            placeholder_text="license.key",
            height=40,
            border_color=COLORS["border"],
            corner_radius=RADIUS,
        )
        self.path.insert(0, "license.key")
        self.path.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        self.ctk.CTkButton(
            path_row,
            text="Browse",
            width=96,
            height=40,
            command=self._browse,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
        ).grid(row=0, column=1)

        self.gen = self.ctk.CTkButton(
            self.frame,
            text="Generate License",
            height=46,
            font=self.fonts["body_bold"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=("white", "white"),
            command=self._on_generate,
        )
        self.gen.grid(
            row=1, column=0, sticky="ew", padx=SPACING["xl"], pady=(SPACING["lg"], 0)
        )

        self.progress = self.ctk.CTkProgressBar(self.frame)
        self.progress.grid(
            row=2, column=0, sticky="ew", padx=SPACING["xl"], pady=(SPACING["sm"], 0)
        )
        self.progress.set(0)
        self.progress.grid_remove()

        self.result = ResultPanel(self.frame, self.ctk, self.fonts, self._copy)
        self.result.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=SPACING["xl"],
            pady=(SPACING["lg"], SPACING["xl"]),
        )
        self.result.grid_remove()

    # -- callbacks -------------------------------------------------------
    def _on_type(self, choice: str) -> None:
        if choice == "TRIAL":
            self.trial.set_state("normal")
            self.trial.clear_error()
        else:
            self.trial.set_state("disabled")

    def _browse(self) -> None:
        from tkinter import filedialog

        p = filedialog.asksaveasfilename(
            defaultextension=".key",
            filetypes=[("License key", "*.key"), ("All files", "*.*")],
            initialfile=self.path.get() or "license.key",
        )
        if p:
            self.path.delete(0, "end")
            self.path.insert(0, p)

    def _copy(self, text: str, btn, original: str) -> None:
        if not text:
            return
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(text)
        self.app.root.update()
        btn.configure(text="Copied ✓")
        self.app.root.after(1200, lambda: btn.configure(text=original))

    def _on_generate(self) -> None:
        hardware_id = self.hwid.get()
        cafe_name = self.cafe.get()
        license_type = self.type.get()
        output_path = self.path.get().strip() or "license.key"

        self.hwid.clear_error()
        self.cafe.clear_error()
        self.trial.clear_error()

        errors = validate_inputs(
            hardware_id, cafe_name, license_type, self.trial.entry.get()
        )
        if "hardware_id" in errors:
            self.hwid.set_error(errors["hardware_id"])
        if "cafe_name" in errors:
            self.cafe.set_error(errors["cafe_name"])
        if "trial_days" in errors:
            self.trial.set_error(errors["trial_days"])
        if errors:
            self.app.show_status("Please fix the highlighted fields.", "error")
            return

        try:
            trial_days = (
                parse_trial_days(self.trial.entry.get())
                if license_type == "TRIAL"
                else None
            )
        except ValueError:
            self.trial.set_error("Trial Days must be a positive number.")
            self.app.show_status("Trial Days must be a positive number.", "error")
            return

        # Loading state; run crypto/file I/O off the UI thread.
        self.gen.configure(state="disabled", text="Generating…")
        self.progress.grid()
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self.app.show_status("Generating…", "busy")

        def work() -> None:
            try:
                blob = build_and_write_license(
                    hardware_id=hardware_id,
                    cafe_name=cafe_name,
                    license_type=license_type,
                    trial_days=trial_days,
                    output_path=output_path,
                )
                self.app.root.after(
                    0,
                    lambda: self._done(
                        blob, output_path, hardware_id, cafe_name, license_type
                    ),
                )
            except Exception as exc:  # includes KeygenError
                msg = str(exc)
                self.app.root.after(0, lambda: self._fail(msg))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, blob, output_path, hardware_id, cafe_name, license_type) -> None:
        issued = date.today().isoformat()
        verify = format_verify_command(output_path)
        try:
            env = json.loads(base64.b64decode(blob))
            expires = env["payload"].get("trial_expires_at")
        except Exception:
            expires = None

        self.gen.configure(state="normal", text="Generate License")
        self.progress.stop()
        self.progress.grid_remove()
        self.result.show(
            cafe=cafe_name,
            hwid=hardware_id,
            ltype=license_type,
            issued=issued,
            expires=expires,
            blob=blob,
            verify=verify,
        )
        self.result.grid()
        self.app.recent.insert(
            0,
            {
                "cafe": cafe_name,
                "hwid": hardware_id,
                "type": license_type,
                "path": output_path,
                "blob": blob,
            },
        )
        self.app.show_status("License generated successfully.", "success")
        show_toast(self.app, "License generated", "success", self.fonts)

    def _fail(self, message: str) -> None:
        self.gen.configure(state="normal", text="Generate License")
        self.progress.stop()
        self.progress.grid_remove()
        self.app.show_status(message, "error")
        from tkinter import messagebox

        messagebox.showerror("License generation failed", message)
