"""Visual theme + brand assets for the Arcade Launcher (CustomTkinter).

Centralizes colors, fonts, and the logo so all launcher screens stay
consistent with the Arcade web app's blue/slate design system
(see frontend/src/index.css and components/ui/Button.tsx).

UI/UX follows the guidance: a single primary CTA per screen,
visible pointer/focus affordances, >=4.5:1 text contrast (the light-mode
muted tone is darkened for this), and error/empty states with clear
recovery microcopy.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from tkinter import font as tkfont

import customtkinter as ctk

try:
    from PIL import Image
except Exception:  # pragma: no cover - headless environments
    Image = None

try:
    import cairosvg  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    cairosvg = None

_LAUNCHER_DIR = Path(__file__).resolve().parent
BRAND_LOGO_SVG = _LAUNCHER_DIR / "frontend" / "public" / "arcade_icon.svg"
LOGO_LIGHT_PNG = _LAUNCHER_DIR / "arcade_logo_light.png"
LOGO_WHITE_PNG = _LAUNCHER_DIR / "arcade_logo_white.png"
GRADIENT_STRIP = _LAUNCHER_DIR / "tools" / "keygen" / "icon" / "arcade_gradient_3px.png"

COLORS = {
    "bg_primary": ("#F8F9FC", "#0E0E12"),
    "bg_secondary": ("#FFFFFF", "#17171C"),
    "bg_tertiary": ("#F1F2F6", "#202027"),
    "text_primary": ("#1A1A20", "#F4F4F6"),
    "text_secondary": ("#5B5B66", "#A0A0AB"),
    "text_disabled": ("#A8A8B2", "#5B5B66"),
    "text_on_accent": ("#FFFFFF", "#FFFFFF"),
    "accent": ("#6366F1", "#818CF8"),
    "accent_fill": ("#5E62F2", "#4F46E5"),
    "accent_fill_hover": ("#4F46E5", "#4338CA"),
    "success": ("#16A34A", "#22C55E"),
    "warning": ("#D97706", "#F59E0B"),
    "error": ("#DC2626", "#EF4444"),
    "border": ("#E6E7EC", "#2A2A32"),
}

RADIUS = 10
BTN_HEIGHT = 44
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}

_CONTRAST_PAIRS = [
    ("text_primary", "bg_primary"),
    ("text_secondary", "bg_primary"),
    ("text_primary", "bg_secondary"),
    ("text_on_accent", "accent_fill"),
    ("text_on_accent", "accent_fill_hover"),
]
_BODY_MIN = 4.5


def _resolve_display_font() -> str | None:
    fonts_dir = _LAUNCHER_DIR / "fonts"
    if not fonts_dir.is_dir():
        return None
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        try:
            tkfont.Font(file=str(ttf))
            return ttf.stem
        except Exception:  # noqa: S112
            continue
    return None


DISPLAY_FONT = _resolve_display_font()


def _system_sans() -> str:
    if sys.platform == "darwin":
        return "Helvetica Neue"
    if sys.platform == "win32":
        return "Segoe UI"
    return "DejaVu Sans"


def load_font_family(ctk) -> str:
    ttf = _LAUNCHER_DIR / "fonts" / "Inter-Variable.ttf"
    if ttf.exists():
        try:
            ctk.FontManager.load_font(str(ttf))
            return "Inter"
        except Exception:  # noqa: S110
            pass
    return _system_sans()


def make_fonts(ctk) -> dict:
    family = load_font_family(ctk)
    display = DISPLAY_FONT or family
    return {
        "h1": ctk.CTkFont(family=display, size=22, weight="bold"),
        "h2": ctk.CTkFont(family=family, size=15, weight="bold"),
        "body": ctk.CTkFont(family=family, size=13),
        "body_bold": ctk.CTkFont(family=family, size=13, weight="bold"),
        "caption": ctk.CTkFont(family=family, size=11),
        "mono": ctk.CTkFont(family="monospace", size=11),
    }


def _relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(c1: str, c2: str) -> float:
    l1, l2 = _relative_luminance(c1), _relative_luminance(c2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def assert_contrast(body_min: float = _BODY_MIN) -> None:
    """Dev-only. Raise AssertionError if any critical pair fails WCAG AA."""
    for text_tok, bg_tok in _CONTRAST_PAIRS:
        light = _contrast(COLORS[text_tok][0], COLORS[bg_tok][0])
        dark = _contrast(COLORS[text_tok][1], COLORS[bg_tok][1])
        assert light >= body_min, f"{text_tok}/{bg_tok} light {light:.2f} < {body_min}"  # noqa: S101
        assert dark >= body_min, f"{text_tok}/{bg_tok} dark {dark:.2f} < {body_min}"  # noqa: S101


def dark_svg(svg_text: str) -> str:
    """Drop the gradient-filled background square to transparent, leaving only
    the white controller glyph — used for the dark-mode logo variant."""
    return re.sub(
        r'<rect[^>]*fill="url\(#brandGradient\)"[^>]*/>',
        '<rect width="24" height="24" rx="5" ry="5" fill="none"/>',
        svg_text,
    )


def rasterize_logo(size: int, dark: bool):
    """Return a PIL RGBA Image of the logo, or None on any failure.
    Uses cairosvg when available; otherwise the committed PNG fallback."""
    if cairosvg is not None and BRAND_LOGO_SVG.is_file():
        try:
            svg = BRAND_LOGO_SVG.read_text(encoding="utf-8")
            if dark:
                svg = dark_svg(svg)
            png = cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                output_width=size,
                output_height=size,
            )
            return Image.open(io.BytesIO(png)).convert("RGBA")
        except Exception:  # noqa: S110
            pass
    png_path = LOGO_WHITE_PNG if dark else LOGO_LIGHT_PNG
    if Image is not None and png_path.is_file():
        try:
            return Image.open(png_path).convert("RGBA")
        except Exception:
            return None
    return None


def load_logo(size: int = 44):
    """Return a CTkImage with light/dark variants, or None if unavailable.
    Headless-safe: never raises."""
    if Image is None:
        return None
    try:
        light = rasterize_logo(size, dark=False)
        dark = rasterize_logo(size, dark=True)
        if light is None and dark is None:
            return None
        return ctk.CTkImage(
            light_image=light,
            dark_image=dark or light,
            size=(size, size),
        )
    except Exception:
        return None
