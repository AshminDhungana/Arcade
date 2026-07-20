# tools/keygen/license_gui/widgets.py
from __future__ import annotations

from .theme import COLORS, RADIUS, SPACING


class Card:
    """A surface card: bg_secondary fill, 1px border, single radius."""

    def __new__(cls, master, ctk, **kw):
        frame = ctk.CTkFrame(
            master,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=RADIUS,
            **kw,
        )
        frame.grid_columnconfigure(0, weight=1)
        return frame


class LabeledField:
    """Label + entry + inline error. Clears error on focus-out via caller."""

    def __init__(
        self, master, ctk, fonts, label, required=False, placeholder="", height=40
    ):
        self.ctk = ctk
        self.fonts = fonts
        self.root = ctk.CTkFrame(master, fg_color="transparent")
        self.root.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text=label,
            font=fonts["body_bold"],
            text_color=COLORS["text_primary"],
        ).pack(side="left")
        if required:
            ctk.CTkLabel(
                header, text="*", font=fonts["body_bold"], text_color=COLORS["error"]
            ).pack(side="left", padx=(3, 0))

        self.entry = ctk.CTkEntry(
            self.root,
            placeholder_text=placeholder,
            height=height,
            border_color=COLORS["border"],
            corner_radius=RADIUS,
        )
        self.entry.grid(row=1, column=0, sticky="ew", pady=(SPACING["xs"], 0))
        self.error = ctk.CTkLabel(
            self.root, text="", font=fonts["caption"], text_color=COLORS["error"]
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


class SegmentedControl:
    """Two-option segmented toggle (Perpetual | Trial)."""

    def __init__(self, master, ctk, fonts, options, default, on_change=None):
        self.ctk = ctk
        self.options = options
        self.on_change = on_change
        self.value = default
        self._buttons = {}
        self.root = ctk.CTkFrame(
            master, fg_color=COLORS["bg_tertiary"], corner_radius=RADIUS
        )
        for opt in options:
            active = opt == default
            btn = ctk.CTkButton(
                self.root,
                text=opt,
                height=34,
                corner_radius=RADIUS - 2,
                fg_color=COLORS["accent"] if active else "transparent",
                text_color=("white", "white") if active else COLORS["text_primary"],
                hover_color=COLORS["accent_hover"],
                command=lambda o=opt: self._select(o),
            )
            btn.pack(
                side="left",
                padx=SPACING["xs"],
                pady=SPACING["xs"],
                expand=True,
                fill="x",
            )
            self._buttons[opt] = btn

    def grid(self, **kw):
        self.root.grid(**kw)

    def _select(self, opt):
        self.value = opt
        for o, btn in self._buttons.items():
            active = o == opt
            btn.configure(
                fg_color=COLORS["accent"] if active else "transparent",
                text_color=("white", "white") if active else COLORS["text_primary"],
            )
        if self.on_change:
            self.on_change(opt)

    def get(self):
        return self.value

    def set(self, opt):
        self._select(opt)


class ResultPanel:
    """Dedicated license-preview / verification panel, revealed on success."""

    def __init__(self, master, ctk, fonts, on_copy):
        self.ctk = ctk
        self.fonts = fonts
        self.on_copy = on_copy
        self._blob = ""
        self._verify = ""
        self.root = ctk.CTkFrame(
            master,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=RADIUS,
        )
        self.root.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.root,
            text="Result",
            font=fonts["h2"],
            text_color=COLORS["text_primary"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )
        self.meta = ctk.CTkLabel(
            self.root,
            text="",
            font=fonts["caption"],
            text_color=COLORS["text_secondary"],
            justify="left",
        )
        self.meta.grid(
            row=1, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["sm"])
        )
        self.box = ctk.CTkTextbox(
            self.root,
            height=120,
            state="disabled",
            font=ctk.CTkFont(family="Courier New", size=11),
        )
        self.box.grid(
            row=2, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["sm"])
        )
        row = ctk.CTkFrame(self.root, fg_color="transparent")
        row.grid(
            row=3, column=0, sticky="ew", padx=SPACING["lg"], pady=(0, SPACING["lg"])
        )
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)
        self.copy_blob = ctk.CTkButton(
            row,
            text="Copy License String",
            height=36,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            command=lambda: self.on_copy(
                self._blob, self.copy_blob, "Copy License String"
            ),
        )
        self.copy_blob.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["xs"]))
        self.copy_verify = ctk.CTkButton(
            row,
            text="Copy Verify Command",
            height=36,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            command=lambda: self.on_copy(
                self._verify, self.copy_verify, "Copy Verify Command"
            ),
        )
        self.copy_verify.grid(row=0, column=1, sticky="ew", padx=(SPACING["xs"], 0))

    def grid(self, **kw):
        self.root.grid(**kw)

    def grid_remove(self):
        self.root.grid_remove()

    def show(self, *, cafe, hwid, ltype, issued, expires, blob, verify):
        self._blob = blob
        self._verify = verify
        exp = expires if expires else "— (perpetual)"
        self.meta.configure(
            text=f"Cafe: {cafe}    HWID: {hwid}\n"
            f"Type: {ltype}    Issued: {issued}    Expires: {exp}"
        )
        self.box.configure(state="normal")
        self.box.delete("0.0", "end")
        self.box.insert("0.0", blob)
        self.box.configure(state="disabled")


class StatusBar:
    """Thin bottom bar: status icon + text (left), hint (right)."""

    _ICONS = {"info": "●", "success": "✓", "error": "✕", "busy": "◌"}
    _KINDS = {
        "info": "text_secondary",
        "success": "success",
        "error": "error",
        "busy": "warning",
    }

    def __init__(self, master, ctk, fonts):
        self.ctk = ctk
        self.fonts = fonts
        self.root = ctk.CTkFrame(
            master, fg_color=COLORS["bg_secondary"], corner_radius=0, height=34
        )
        self.icon = ctk.CTkLabel(
            self.root,
            text="●",
            font=fonts["caption"],
            text_color=COLORS["text_secondary"],
        )
        self.icon.pack(side="left", padx=(SPACING["lg"], SPACING["xs"]))
        self.text = ctk.CTkLabel(
            self.root,
            text="",
            font=fonts["caption"],
            text_color=COLORS["text_secondary"],
        )
        self.text.pack(side="left")
        self.hint = ctk.CTkLabel(
            self.root,
            text="",
            font=fonts["caption"],
            text_color=COLORS["text_disabled"],
        )
        self.hint.pack(side="right", padx=(0, SPACING["lg"]))

    def grid(self, **kw):
        self.root.grid(**kw)

    def set(self, text, kind="info"):
        col = COLORS[self._KINDS[kind]]
        self.text.configure(text=text, text_color=col)
        self.icon.configure(text=self._ICONS[kind], text_color=col)


class NavButton:
    """Sidebar navigation item with active highlight."""

    def __init__(self, master, ctk, fonts, label, key, command):
        self.ctk = ctk
        self.key = key
        self.btn = ctk.CTkButton(
            master,
            text=label,
            height=38,
            anchor="w",
            corner_radius=RADIUS,
            fg_color="transparent",
            hover_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            font=fonts["body"],
            command=command,
        )

    def grid(self, **kw):
        self.btn.grid(**kw)

    def set_active(self, active):
        self.btn.configure(
            fg_color=COLORS["accent"] if active else "transparent",
            text_color=("white", "white") if active else COLORS["text_primary"],
        )


def show_toast(app, message, kind="info", fonts=None, duration_ms=2500):
    """Borderless, self-destructing toast pinned to the app's bottom-right."""
    ctk = app.ctk
    fonts = fonts or app.fonts
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
        text_color="white",
        corner_radius=RADIUS,
        font=fonts["body"],
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
