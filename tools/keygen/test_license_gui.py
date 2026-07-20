from tools.keygen.license_gui.theme import COLORS


def test_theme_tokens_are_light_dark_tuples():
    for name, value in COLORS.items():
        assert isinstance(value, tuple) and len(value) == 2, name
        assert all(isinstance(c, str) and c.startswith("#") for c in value), name
