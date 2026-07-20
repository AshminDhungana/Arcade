# tests/launcher/test_theme.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import launcher_theme as theme


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
