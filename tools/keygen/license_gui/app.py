# tools/keygen/license_gui/app.py
from __future__ import annotations

from pathlib import Path

try:
    from ..generate_license import PRIVATE_KEY_PATH
    from ..license_helpers import resolve_logo_path
    from .theme import COLORS, SPACING, make_fonts
    from .views.keys import KeysView
    from .views.new_license import NewLicenseView
    from .views.recent import RecentView
    from .widgets import NavButton, StatusBar
except ImportError:  # direct `python generate_license.py` run: no parent package
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from generate_license import PRIVATE_KEY_PATH
    from license_helpers import resolve_logo_path

    from .theme import COLORS, SPACING, make_fonts
    from .views.keys import KeysView
    from .views.new_license import NewLicenseView
    from .views.recent import RecentView
    from .widgets import NavButton, StatusBar


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
    def __init__(self, ctk) -> None:
        self.ctk = ctk
        self.root = ctk.CTk()
        self.root.title("Arcade License Generator")
        self.root.geometry("960x680")
        self.root.minsize(860, 620)
        self.root.resizable(True, True)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self.fonts = make_fonts(ctk)
        self.recent: list[dict] = []
        self.views: dict[str, object] = {}
        self.nav: dict[str, NavButton] = {}

        self._build_topbar()
        self._build_body()
        self._build_footer()
        self.show_view("new")

    # -- top bar ---------------------------------------------------------
    def _build_topbar(self) -> None:
        ctk = self.ctk
        bar = ctk.CTkFrame(self.root, fg_color=COLORS["bg_secondary"], corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)
        bar.grid_rowconfigure(2, minsize=3)

        logo = resolve_logo_path()
        if logo:
            try:
                from PIL import Image

                img = Image.open(logo)
                self.logo = ctk.CTkImage(light_image=img, dark_image=img, size=(40, 40))
                ctk.CTkLabel(bar, image=self.logo, text="").grid(
                    row=0,
                    column=0,
                    rowspan=2,
                    padx=(SPACING["lg"], SPACING["sm"]),
                    pady=SPACING["md"],
                )
            except Exception:  # noqa: S110 - best effort logo loading
                pass

        ctk.CTkLabel(
            bar, text="Arcade", font=self.fonts["h1"], text_color=COLORS["text_primary"]
        ).grid(row=0, column=1, sticky="w", pady=(SPACING["md"], 0))
        ctk.CTkLabel(
            bar,
            text="License Generator",
            font=self.fonts["caption"],
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=1, sticky="w")

        self.appearance = ctk.CTkOptionMenu(
            bar,
            values=["System", "Dark", "Light"],
            width=110,
            command=self._on_appearance,
        )
        self.appearance.set("System")
        self.appearance.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="e",
            padx=(0, SPACING["sm"]),
            pady=SPACING["md"],
        )

        key_ok = PRIVATE_KEY_PATH.exists()
        self.key_badge = ctk.CTkLabel(
            bar,
            text="Key loaded ✓" if key_ok else "No key ⚠",
            font=self.fonts["caption"],
            text_color=COLORS["success"] if key_ok else COLORS["warning"],
            width=110,
        )
        self.key_badge.grid(
            row=0,
            column=3,
            rowspan=2,
            sticky="e",
            padx=(0, SPACING["lg"]),
            pady=SPACING["md"],
        )

        grad = self._gradient()
        if grad is not None:
            ctk.CTkLabel(bar, image=grad, text="").grid(
                row=2, column=0, columnspan=4, sticky="ew"
            )

    def _gradient(self):
        g = Path(__file__).resolve().parent.parent / "icon" / "arcade_gradient_3px.png"
        if not g.exists():
            return None
        try:
            from PIL import Image

            img = Image.open(g)
            return self.ctk.CTkImage(light_image=img, dark_image=img, size=(900, 3))
        except Exception:
            return None

    def _on_appearance(self, choice: str) -> None:
        self.ctk.set_appearance_mode(choice)

    # -- body (sidebar + content) ---------------------------------------
    def _build_body(self) -> None:
        ctk = self.ctk
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(
            body, fg_color=COLORS["bg_secondary"], corner_radius=0, width=200
        )
        side.grid(row=0, column=0, sticky="ns")
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            side,
            text="MENU",
            font=self.fonts["caption"],
            text_color=COLORS["text_disabled"],
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        for i, (key, label) in enumerate(
            [("new", "New License"), ("recent", "Recent"), ("keys", "Keys")]
        ):
            btn = NavButton(
                side, ctk, self.fonts, label, key, lambda k=key: self.show_view(k)
            )
            btn.grid(
                row=i + 1,
                column=0,
                sticky="ew",
                padx=SPACING["sm"],
                pady=(SPACING["xs"], 0),
            )
            self.nav[key] = btn

        self.content = ctk.CTkFrame(body, fg_color=COLORS["bg_primary"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    # -- footer ----------------------------------------------------------
    def _build_footer(self) -> None:
        self.status = StatusBar(self.root, self.ctk, self.fonts)
        self.status.grid(row=2, column=0, sticky="ew")
        self.status.set("Ready", "info")
        self.status.hint.configure(text="Generate: ⌘/Ctrl+G")

    # -- view switching --------------------------------------------------
    def show_view(self, key: str) -> None:
        for k, v in self.views.items():
            if k != key:
                v.frame.grid_forget()
        if key not in self.views:
            cls = {"new": NewLicenseView, "recent": RecentView, "keys": KeysView}[key]
            self.views[key] = cls(self, self.content)
        view = self.views[key]
        view.frame.grid(row=0, column=0, sticky="nsew")
        for k, btn in self.nav.items():
            btn.set_active(k == key)
        if hasattr(view, "on_show"):
            view.on_show()

    def show_status(self, text: str, kind: str = "info") -> None:
        self.status.set(text, kind)

    def run(self) -> None:
        self.root.mainloop()


def launch_gui() -> None:
    """Entry point used by ``generate_license.main()``. Lazy-imports customtkinter."""
    ctk = _require_customtkinter()
    LicenseApp(ctk).run()
