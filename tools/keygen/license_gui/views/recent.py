# tools/keygen/license_gui/views/recent.py
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    from ...generate_license import format_verify_command
    from ..theme import COLORS, SPACING
    from ..widgets import Card, show_toast
except ImportError:
    from generate_license import format_verify_command

    from ..theme import COLORS, SPACING
    from ..widgets import Card, show_toast


class RecentView:
    def __init__(self, app, master) -> None:
        self.app = app
        self.ctk = app.ctk
        self.fonts = app.fonts

        self.frame = self.ctk.CTkScrollableFrame(master, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)

        self.ctk.CTkLabel(
            self.frame,
            text="Recent — this session",
            font=self.fonts["h2"],
            text_color=COLORS["text_primary"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=SPACING["xl"],
            pady=(SPACING["xl"], SPACING["sm"]),
        )

        self.list = self.ctk.CTkFrame(self.frame, fg_color="transparent")
        self.list.grid(
            row=1, column=0, sticky="ew", padx=SPACING["xl"], pady=(0, SPACING["xl"])
        )
        self.list.grid_columnconfigure(0, weight=1)

    def on_show(self) -> None:
        self._render()

    def _render(self) -> None:
        for child in self.list.winfo_children():
            child.destroy()
        if not self.app.recent:
            self.ctk.CTkLabel(
                self.list,
                text="No licenses generated yet — switch to New License.",
                font=self.fonts["caption"],
                text_color=COLORS["text_secondary"],
            ).grid(row=0, column=0, sticky="w", pady=SPACING["md"])
            return
        for i, rec in enumerate(self.app.recent):
            row = Card(self.list, self.ctk)
            row.grid(row=i, column=0, sticky="ew", pady=(0, SPACING["sm"]))
            self.ctk.CTkLabel(
                row,
                text=rec["cafe"],
                font=self.fonts["body_bold"],
                text_color=COLORS["text_primary"],
            ).grid(
                row=0, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["md"], 0)
            )
            self.ctk.CTkLabel(
                row,
                text=f"{rec['type']} · {rec['hwid']}",
                font=self.fonts["caption"],
                text_color=COLORS["text_secondary"],
            ).grid(
                row=1, column=0, sticky="w", padx=SPACING["md"], pady=(0, SPACING["sm"])
            )
            btns = self.ctk.CTkFrame(row, fg_color="transparent")
            btns.grid(row=0, column=1, rowspan=2, sticky="e", padx=SPACING["md"])
            self.ctk.CTkButton(
                btns,
                text="Copy",
                width=72,
                height=32,
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                border_width=1,
                border_color=COLORS["border"],
                command=lambda r=rec: self._copy(r["blob"]),
            ).pack(side="left", padx=(0, SPACING["xs"]))
            self.ctk.CTkButton(
                btns,
                text="Verify",
                width=72,
                height=32,
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                border_width=1,
                border_color=COLORS["border"],
                command=lambda r=rec: self._copy_verify(r["path"]),
            ).pack(side="left")
            self.ctk.CTkButton(
                btns,
                text="Open",
                width=72,
                height=32,
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                border_width=1,
                border_color=COLORS["border"],
                command=lambda r=rec: self._open(r["path"]),
            ).pack(side="left", padx=(SPACING["xs"], 0))

    def _copy(self, blob: str) -> None:
        if not blob:
            return
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(blob)
        self.app.root.update()

    def _copy_verify(self, path: str) -> None:
        cmd = format_verify_command(path)
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(cmd)
        self.app.root.update()
        show_toast(self.app, "Verify command copied", "info", self.fonts)

    def _open(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            show_toast(self.app, "File not found", "error", self.fonts)
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/c", "start", "", str(p)])  # noqa: S603, S607
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])  # noqa: S603, S607
            else:
                subprocess.Popen(["xdg-open", str(p)])  # noqa: S603, S607
        except Exception as exc:
            show_toast(self.app, str(exc), "error", self.fonts)
