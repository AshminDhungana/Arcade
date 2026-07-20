# tools/keygen/license_gui/views/keys.py
from __future__ import annotations

try:
    from ...generate_license import PRIVATE_KEY_PATH
    from ..theme import COLORS, SPACING
    from ..widgets import Card
except ImportError:
    from generate_license import PRIVATE_KEY_PATH

    from ..theme import COLORS, SPACING
    from ..widgets import Card


class KeysView:
    def __init__(self, app, master) -> None:
        self.app = app
        self.ctk = app.ctk
        self.fonts = app.fonts

        self.frame = self.ctk.CTkScrollableFrame(master, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=1)

        card = Card(self.frame, self.ctk)
        card.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=SPACING["xl"],
            pady=(SPACING["xl"], SPACING["xl"]),
        )

        self.ctk.CTkLabel(
            card,
            text="Signing Key",
            font=self.fonts["h2"],
            text_color=COLORS["text_primary"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        if PRIVATE_KEY_PATH.exists():
            self.ctk.CTkLabel(
                card,
                text="✓ Private key loaded. Licenses can be signed.",
                font=self.fonts["body"],
                text_color=COLORS["success"],
            ).grid(
                row=1, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["sm"])
            )
            self.ctk.CTkLabel(
                card,
                text=f"Location: {PRIVATE_KEY_PATH}",
                font=self.fonts["caption"],
                text_color=COLORS["text_secondary"],
            ).grid(
                row=2, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["lg"])
            )
        else:
            self.ctk.CTkLabel(
                card,
                text="⚠ No private key found.",
                font=self.fonts["body_bold"],
                text_color=COLORS["warning"],
            ).grid(
                row=1, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["sm"])
            )
            self.ctk.CTkLabel(
                card,
                text="Run the key generator first:",
                font=self.fonts["body"],
                text_color=COLORS["text_primary"],
            ).grid(row=2, column=0, sticky="w", padx=SPACING["lg"])
            self.ctk.CTkLabel(
                card,
                text="python -m tools.keygen.generate_keys",
                font=self.fonts["body"],
                text_color=COLORS["text_secondary"],
            ).grid(
                row=3,
                column=0,
                sticky="w",
                padx=SPACING["lg"],
                pady=(SPACING["xs"], SPACING["sm"]),
            )
            self.ctk.CTkLabel(
                card,
                text=(
                    "INTERNAL USE ONLY — the private key must never "
                    "be committed or shipped."
                ),
                font=self.fonts["caption"],
                text_color=COLORS["text_disabled"],
            ).grid(
                row=4, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["lg"])
            )
