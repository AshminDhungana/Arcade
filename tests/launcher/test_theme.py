import tkinter

# Importing launcher_theme pulls in customtkinter, which only needs a display
# when widgets/images are *instantiated*. The import itself is safe headless,
# but the logo test instantiates CTkImage, so guard on display availability.
try:
    import launcher_theme  # noqa: E402
except Exception:  # pragma: no cover - import environment issue
    launcher_theme = None  # type: ignore[assignment]

import pytest

pytestmark = pytest.mark.skipif(
    launcher_theme is None, reason="launcher_theme (customtkinter) not importable"
)


def _has_display() -> bool:
    try:
        tkinter.Tk().destroy()
        return True
    except Exception:
        return False


def test_constants_defined():
    assert launcher_theme.BLUE == "#2563EB"
    assert launcher_theme.BLUE_HOVER == "#3B82F6"
    assert launcher_theme.EMERALD == "#059669"
    assert launcher_theme.RED == "#DC2626"
    assert launcher_theme.S900 == "#0F172A"
    assert launcher_theme.TEXT == "#F8FAFC"
    assert launcher_theme.RADIUS == 8
    assert launcher_theme.BTN_HEIGHT == 44
    # Light-mode muted tone is darkened for >=4.5:1 contrast on near-white.
    assert launcher_theme.MUTED_TEXT == ["#64748B", "#94A3B8"]
    # No bundled fonts/ dir in this repo -> system default font.
    assert launcher_theme.BRAND_FONT is None


def test_load_logo_present_when_asset_exists():
    if not launcher_theme.BRAND_LOGO_PATH.is_file():
        pytest.skip("logo asset not present")
    if not _has_display():
        pytest.skip("no display available")
    img = launcher_theme.load_logo(64)
    assert img is not None


def test_load_logo_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "launcher_theme.BRAND_LOGO_PATH", tmp_path / "does_not_exist.png"
    )
    assert launcher_theme.load_logo(64) is None
