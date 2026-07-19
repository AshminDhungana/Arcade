"""Visual theme + brand assets for the Arcade Launcher (CustomTkinter).

Centralizes colors, fonts, and the logo so all launcher screens stay
consistent with the Arcade web app's blue/slate design system
(see frontend/src/index.css and components/ui/Button.tsx).

UI/UX follows the ui-ux-pro-max guidance: a single primary CTA per screen,
visible pointer/focus affordances, >=4.5:1 text contrast (the light-mode
muted tone is darkened for this), and error/empty states with clear
recovery microcopy.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import font as tkfont

import customtkinter as ctk

try:
    from PIL import Image
except Exception:  # pragma: no cover - headless environments
    Image = None

# ── Paths ────────────────────────────────────────────────────────────────
_LAUNCHER_DIR = Path(__file__).resolve().parent
BRAND_LOGO_PATH = _LAUNCHER_DIR / "frontend" / "public" / "icon_opc.png"

# ── Palette (mirrors frontend/src/index.css @theme) ───────────────────────
# Dark-mode surfaces / text
S900 = "#0F172A"  # surface-900  window/frame bg (dark)
S800 = "#1E293B"  # surface-800  raised surfaces (dark)
S700 = "#334155"  # surface-700  borders / secondary (dark)
TEXT = "#F8FAFC"  # text-50
MUTED = "#94A3B8"  # text-muted  (dark mode)
# Light-mode surfaces / text
L_BG = "#F1F5F9"  # slate-100  window bg (light)
L_FRAME = "#FFFFFF"
L_TEXT = "#0F172A"  # slate-900
L_BORDER = "#CBD5E1"  # slate-300
# Brand / actions
BLUE = "#2563EB"  # brand-600  primary
BLUE_HOVER = "#3B82F6"  # brand-500
EMERALD = "#059669"  # emerald-600  start
EMERALD_HOVER = "#10B981"
RED = "#DC2626"  # red-600  stop / error
RED_HOVER = "#EF4444"
S700_HOVER = "#475569"  # slate-600
# Shape / sizing
RADIUS = 8
BTN_HEIGHT = 44

# Text colors as (light, dark) tuples so contrast holds in both themes.
# MUTED is lightened in dark mode but DARKENED in light mode: #94A3B8 on
# near-white only reaches ~2.6:1, so the light variant uses slate-500.
MUTED_TEXT = ["#64748B", MUTED]


# ── Optional bundled display font (gaming/esports brand energy) ───────────
def _resolve_brand_font() -> str | None:
    """Register a bundled .ttf (e.g. Chakra Petch / Russo One) if present.

    Drop a font into a `fonts/` folder beside launcher.py. Returns the
    registered family name, or None to use the system default. Never raises
    (cross-platform safe; a missing/unreadable file is simply skipped).
    """
    fonts_dir = _LAUNCHER_DIR / "fonts"
    if not fonts_dir.is_dir():
        return None
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        try:
            tkfont.Font(file=str(ttf))
            return ttf.stem
        except Exception:
            continue
    return None


BRAND_FONT = _resolve_brand_font()


def _font(size: int, *, bold: bool = False) -> ctk.CTkFont:
    kwargs: dict = {"size": size, "weight": "bold" if bold else "normal"}
    if BRAND_FONT:
        kwargs["family"] = BRAND_FONT
    return ctk.CTkFont(**kwargs)


# ── Fonts ─────────────────────────────────────────────────────────────────
def heading_font(size: int = 14) -> ctk.CTkFont:
    return _font(size, bold=True)


def title_font(size: int = 22) -> ctk.CTkFont:
    return _font(size, bold=True)


def body_font(size: int = 12) -> ctk.CTkFont:
    return _font(size)


def mono_font(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family="monospace", size=size)


def wordmark_font(size: int = 18) -> ctk.CTkFont:
    return _font(size, bold=True)


# ── Logo ──────────────────────────────────────────────────────────────────
def load_logo(size: int = 64) -> ctk.CTkImage | None:
    """Load the transparent brand logo. Returns None if the asset is absent so
    callers can fall back to a text-only header (launcher must still open)."""
    if not BRAND_LOGO_PATH.is_file():
        return None
    if Image is None:
        return None
    try:
        # Same transparent PNG on both themes (no background to clash).
        pil_image = Image.open(BRAND_LOGO_PATH).convert("RGBA")
        return ctk.CTkImage(
            light_image=pil_image,
            dark_image=pil_image,
            size=(size, size),
        )
    except Exception:
        return None


# ── Reusable branded header ────────────────────────────────────────────────
def brand_header(parent: ctk.CTkBaseClass, *, subtitle: str) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.columnconfigure(1, weight=1)

    logo = load_logo(44)
    if logo is not None:
        ctk.CTkLabel(frame, image=logo, text="").grid(
            row=0, column=0, rowspan=2, padx=(0, 10), pady=8, sticky="w"
        )

    ctk.CTkLabel(frame, text="ARCADE", font=wordmark_font(18), text_color=BLUE).grid(
        row=0, column=1, sticky="w", pady=(6, 0)
    )
    ctk.CTkLabel(frame, text=subtitle, font=body_font(11), text_color=MUTED_TEXT).grid(
        row=1, column=1, sticky="w"
    )
    ctk.CTkFrame(frame, height=2, fg_color=BLUE).grid(
        row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0)
    )
    return frame


__all__ = [
    "BRAND_LOGO_PATH",
    "BLUE",
    "BLUE_HOVER",
    "EMERALD",
    "EMERALD_HOVER",
    "RED",
    "RED_HOVER",
    "S700",
    "S700_HOVER",
    "S800",
    "S900",
    "TEXT",
    "MUTED",
    "MUTED_TEXT",
    "RADIUS",
    "BTN_HEIGHT",
    "BRAND_FONT",
    "heading_font",
    "title_font",
    "body_font",
    "mono_font",
    "wordmark_font",
    "load_logo",
    "brand_header",
]
