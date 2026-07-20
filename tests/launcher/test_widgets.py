import os
import sys
from pathlib import Path

import customtkinter as ctk
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Construction needs a display; skip on headless CI.
_DISPLAY = bool(os.environ.get("DISPLAY")) or sys.platform == "win32"
pytestmark = pytest.mark.skipif(not _DISPLAY, reason="needs a display")


def test_widgets_construct():
    from launcher_widgets import (
        Card,
        LabeledField,
        StatusBar,
        StepIndicator,
        screen_title,
    )

    root = ctk.CTk()
    root.withdraw()
    fonts = {
        "h1": ctk.CTkFont(size=22, weight="bold"),
        "h2": ctk.CTkFont(size=15, weight="bold"),
        "body": ctk.CTkFont(size=13),
        "body_bold": ctk.CTkFont(size=13, weight="bold"),
        "caption": ctk.CTkFont(size=11),
        "mono": ctk.CTkFont(family="monospace", size=11),
    }
    card = Card(root)
    assert card.winfo_exists()
    field = LabeledField(root, "Café Name", fonts=fonts)
    field.grid()
    field.set_error("Required")
    assert field.get() == ""
    field.clear_error()
    sb = StatusBar(root, fonts)
    sb.set("Ready", "info")
    sb.grid()
    ind = StepIndicator(root, fonts, ["Café", "Staff", "Seats"])
    ind.set_active(1)
    ind.grid()
    title = screen_title(root, fonts, "Server Control", subtitle="Manage the server")
    assert title.winfo_exists()
    root.destroy()
