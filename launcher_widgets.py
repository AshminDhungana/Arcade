"""Reusable indigo-themed widgets for the Arcade Launcher.

Ports Card / LabeledField / StatusBar / Toast from tools/keygen/license_gui/widgets.py
and adds StepIndicator + screen_title. All colors come from launcher_theme.COLORS.
"""

from __future__ import annotations

import customtkinter as ctk

from launcher_theme import COLORS, RADIUS, SPACING


class Card:
    """A surface card: bg_secondary fill, 1px border, single radius."""

    def __new__(cls, master, **kw):
        return ctk.CTkFrame(
            master,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=RADIUS,
            **kw,
        )


class LabeledField:
    """Label + entry + inline error. Clears error on focus-out via caller."""

    def __init__(
        self,
        master,
        label,
        *,
        required=False,
        placeholder="",
        show="",
        height=40,
        fonts=None,
    ):
        fonts = fonts or {}
        self.root = ctk.CTkFrame(master, fg_color="transparent")
        self.root.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text=label,
            font=fonts.get("body_bold"),
            text_color=COLORS["text_primary"],
        ).pack(side="left")
        if required:
            ctk.CTkLabel(
                header,
                text="*",
                font=fonts.get("body_bold"),
                text_color=COLORS["error"],
            ).pack(side="left", padx=(3, 0))

        self.entry = ctk.CTkEntry(
            self.root,
            placeholder_text=placeholder,
            show=show or None,
            height=height,
            border_color=COLORS["border"],
            corner_radius=RADIUS,
            font=fonts.get("body"),
            fg_color=COLORS["bg_secondary"],
            text_color=COLORS["text_primary"],
        )
        self.entry.grid(row=1, column=0, sticky="ew", pady=(SPACING["xs"], 0))
        self.error = ctk.CTkLabel(
            self.root, text="", font=fonts.get("caption"), text_color=COLORS["error"]
        )
        self.error.grid(row=2, column=0, sticky="w")
        self.error.grid_remove()

    def grid(self, **kw):
        self.root.grid(**kw)

    def get(self):
        return self.entry.get().strip()

    def set_error(self, msg):
        self.error.configure(text=msg)
        self.error.grid()
        self.entry.configure(border_color=COLORS["error"])

    def clear_error(self):
        self.error.grid_remove()
        self.entry.configure(border_color=COLORS["border"])

    def set_state(self, state):
        self.entry.configure(state=state)


class StatusBar:
    """Thin bottom bar: status icon + text (left), hint (right). Color + symbol."""

    _ICONS = {"info": "●", "success": "✓", "error": "✕", "busy": "◌"}
    _KINDS = {
        "info": "text_secondary",
        "success": "success",
        "error": "error",
        "busy": "warning",
    }

    def __init__(self, master, fonts):
        self.fonts = fonts
        self.root = ctk.CTkFrame(
            master, fg_color=COLORS["bg_secondary"], corner_radius=0, height=34
        )
        self.icon = ctk.CTkLabel(
            self.root,
            text="●",
            font=fonts.get("caption"),
            text_color=COLORS["text_secondary"],
        )
        self.icon.pack(side="left", padx=(SPACING["lg"], SPACING["xs"]))
        self.text = ctk.CTkLabel(
            self.root,
            text="",
            font=fonts.get("caption"),
            text_color=COLORS["text_secondary"],
        )
        self.text.pack(side="left")
        self.hint = ctk.CTkLabel(
            self.root,
            text="",
            font=fonts.get("caption"),
            text_color=COLORS["text_disabled"],
        )
        self.hint.pack(side="right", padx=(0, SPACING["lg"]))

    def grid(self, **kw):
        self.root.grid(**kw)

    def set(self, text, kind="info"):
        col = COLORS[self._KINDS.get(kind, "text_secondary")]
        self.text.configure(text=text, text_color=col)
        self.icon.configure(text=self._ICONS.get(kind, "●"), text_color=col)


class StepIndicator:
    """Row of numbered chips + connecting lines; highlights steps up to active."""

    def __init__(self, master, fonts, steps):
        self.fonts = fonts
        self._chips = []
        self._labels = []
        self._lines = []
        self.root = ctk.CTkFrame(master, fg_color="transparent")
        n = len(steps)
        for i in range(n * 2 - 1):
            self.root.grid_columnconfigure(i, weight=1)
        for i, label in enumerate(steps):
            col = 2 * i
            if i > 0:
                line = ctk.CTkFrame(
                    self.root, height=2, fg_color=COLORS["border"], corner_radius=0
                )
                line.grid(row=0, column=col - 1, sticky="ew")
                self._lines.append(line)
            chip = ctk.CTkFrame(
                self.root,
                height=30,
                corner_radius=RADIUS,
                fg_color=COLORS["bg_tertiary"],
            )
            chip.grid(row=0, column=col, sticky="ew", padx=SPACING["xs"])
            lab = ctk.CTkLabel(
                chip,
                text=f"{i + 1}. {label}",
                font=fonts.get("caption"),
                text_color=COLORS["text_secondary"],
            )
            lab.pack(expand=True)
            self._chips.append(chip)
            self._labels.append(lab)
        self.set_active(0)

    def grid(self, **kw):
        self.root.grid(**kw)

    def set_active(self, idx):
        for i, (chip, lab) in enumerate(zip(self._chips, self._labels, strict=True)):
            active = i <= idx
            chip.configure(
                fg_color=COLORS["accent_fill"] if active else COLORS["bg_tertiary"]
            )
            lab.configure(
                text_color=COLORS["text_on_accent"]
                if active
                else COLORS["text_secondary"]
            )
        for i, line in enumerate(self._lines):
            line.configure(
                fg_color=COLORS["accent_fill"] if i < idx else COLORS["border"]
            )


def screen_title(parent, fonts, text, subtitle=None):
    """A screen heading (no ARCADE wordmark — the topbar owns that)."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.columnconfigure(0, weight=1)
    ctk.CTkLabel(
        frame, text=text, font=fonts.get("h2"), text_color=COLORS["text_primary"]
    ).grid(row=0, column=0, sticky="w")
    if subtitle:
        ctk.CTkLabel(
            frame,
            text=subtitle,
            font=fonts.get("caption"),
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
    return frame


def show_toast(app, message, kind="info", duration_ms=2500):
    """Borderless, self-destructing toast pinned to the app's bottom-right."""
    col = {
        "info": COLORS["accent"],
        "success": COLORS["success"],
        "error": COLORS["error"],
    }.get(kind, COLORS["accent"])
    toast = ctk.CTkToplevel(app.root)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    label = ctk.CTkLabel(
        toast,
        text=message,
        fg_color=col,
        text_color=COLORS["text_on_accent"],
        corner_radius=RADIUS,
        font=app.fonts.get("body"),
        padx=SPACING["lg"],
        pady=SPACING["sm"],
    )
    label.pack()
    app.root.update_idletasks()
    x = (
        app.root.winfo_rootx()
        + app.root.winfo_width()
        - toast.winfo_reqwidth()
        - SPACING["lg"]
    )
    y = (
        app.root.winfo_rooty()
        + app.root.winfo_height()
        - toast.winfo_reqheight()
        - SPACING["lg"]
        - 40
    )
    toast.geometry(f"+{x}+{y}")
    toast.after(duration_ms, toast.destroy)
