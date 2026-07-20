# tests/launcher/test_theme.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import launcher_theme as theme  # noqa: E402


def test_contrast_pairs_meet_wcag_aa():
    theme.assert_contrast()  # raises AssertionError if any critical pair < 4.5:1


def test_colors_are_light_dark_tuples():
    assert len(theme.COLORS) >= 10
    for value in theme.COLORS.values():
        assert isinstance(value, tuple) and len(value) == 2


def test_spacing_and_shape_constants():
    assert theme.RADIUS == 10
    assert theme.BTN_HEIGHT == 44
    assert theme.SPACING == {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}


def test_dark_svg_drops_gradient_square():
    svg = (
        '<svg><defs><linearGradient id="brandGradient"/></defs>'
        '<rect width="24" height="24" fill="url(#brandGradient)"/>'
        '<path stroke="#ffffff"/></svg>'
    )
    out = theme.dark_svg(svg)
    assert 'fill="url(#brandGradient)"' not in out
    assert 'fill="none"' in out
    assert 'stroke="#ffffff"' in out


def test_rasterize_logo_returns_image_or_none():
    # Headless-safe: never raises; returns a PIL Image when possible, else None.
    result = theme.rasterize_logo(64, dark=False)
    assert result is None or hasattr(result, "convert")
    result_d = theme.rasterize_logo(64, dark=True)
    assert result_d is None or hasattr(result_d, "convert")


def test_load_logo_does_not_raise():
    # Returns a CTkImage or None; must never raise (headless-safe).
    out = theme.load_logo(44)
    assert out is None or out.__class__.__name__ == "CTkImage"
