from __future__ import annotations

import sys
from pathlib import Path

# All colors are (light, dark) tuples so customtkinter auto-switches on appearance mode.
COLORS = {
    "bg_primary": ("#F8F9FC", "#0E0E12"),
    "bg_secondary": ("#FFFFFF", "#17171C"),
    "bg_tertiary": ("#F1F2F6", "#202027"),
    "text_primary": ("#1A1A20", "#F4F4F6"),
    "text_secondary": ("#5B5B66", "#A0A0AB"),
    "text_disabled": ("#A8A8B2", "#5B5B66"),
    "accent": ("#6366F1", "#818CF8"),
    "accent_hover": ("#4F46E5", "#A5B4FC"),
    "success": ("#16A34A", "#22C55E"),
    "warning": ("#D97706", "#F59E0B"),
    "error": ("#DC2626", "#EF4444"),
    "border": ("#E6E7EC", "#2A2A32"),
}

RADIUS = 10
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}


def _system_sans() -> str:
    if sys.platform == "darwin":
        return "Helvetica Neue"
    if sys.platform == "win32":
        return "Segoe UI"
    return "DejaVu Sans"


def load_font_family(ctk) -> str:
    """Return a clean sans family. Uses bundled Inter if present, else system sans."""
    ttf = Path(__file__).resolve().parent.parent / "icon" / "Inter-Variable.ttf"
    if ttf.exists():
        try:
            ctk.FontManager.load_font(str(ttf))
            return "Inter"
        except Exception:  # noqa: S110 — font load is best-effort; fall back to system sans
            pass
    return _system_sans()


def make_fonts(ctk) -> dict:
    """Build the type scale. Call ONLY after a CTk() root exists."""
    family = load_font_family(ctk)
    return {
        "h1": ctk.CTkFont(family=family, size=22, weight="bold"),
        "h2": ctk.CTkFont(family=family, size=15, weight="bold"),
        "body": ctk.CTkFont(family=family, size=13, weight="normal"),
        "body_bold": ctk.CTkFont(family=family, size=13, weight="bold"),
        "caption": ctk.CTkFont(family=family, size=11, weight="normal"),
    }
