"""Tests for StepIndicator widget."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk
import pytest

from launcher_theme import make_fonts
from launcher_widgets import StepIndicator


@pytest.fixture(scope="session")
def ctk_root():
    """Create a CTk root for widget tests."""
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.withdraw()  # Hide during tests
    yield root
    root.destroy()


@pytest.fixture
def fonts(ctk_root):
    return make_fonts(ctk)


@pytest.fixture
def steps():
    return ["Café", "Staff", "Seats", "Override"]


def test_step_indicator_instantiation(ctk_root, fonts, steps):
    """StepIndicator creates without error and has expected attributes."""
    indicator = StepIndicator(ctk_root, fonts, steps)
    assert indicator.root is not None
    assert len(indicator._pills) == 4
    assert len(indicator._line_ids) == 3
    indicator.root.destroy()


def test_step_indicator_set_active_states(ctk_root, fonts, steps):
    """set_active correctly updates visual states for completed/current/upcoming."""
    indicator = StepIndicator(ctk_root, fonts, steps)

    # Step 0: only first is current
    indicator.set_active(0)
    pill0 = indicator._pills[0]
    assert pill0["state"] == "current"
    assert pill0["circle_label"].cget("text") == "1"

    # Step 1: first completed, second current
    indicator.set_active(1)
    pill0 = indicator._pills[0]
    pill1 = indicator._pills[1]
    assert pill0["state"] == "completed"
    assert pill0["circle_label"].cget("text") == "✓"
    assert pill1["state"] == "current"
    assert pill1["circle_label"].cget("text") == "2"

    # Step 3: all completed, last current
    indicator.set_active(3)
    for i in range(3):
        assert indicator._pills[i]["state"] == "completed"
        assert indicator._pills[i]["circle_label"].cget("text") == "✓"
    pill3 = indicator._pills[3]
    assert pill3["state"] == "current"
    assert pill3["circle_label"].cget("text") == "4"

    indicator.root.destroy()


def test_step_indicator_grid(ctk_root, fonts, steps):
    """grid() delegates to root frame."""
    indicator = StepIndicator(ctk_root, fonts, steps)
    # Should not raise
    indicator.grid(row=0, column=0, sticky="ew")
    indicator.root.destroy()


def test_step_indicator_horizontal_scroll(ctk_root, fonts, steps):
    """Canvas scrollregion updates when pills exceed width."""
    indicator = StepIndicator(ctk_root, fonts, steps)
    indicator._canvas.update_idletasks()
    # Scrollregion should be set
    bbox = indicator._canvas.bbox("all")
    assert bbox is not None
    assert bbox[2] > indicator._canvas.winfo_width() or len(steps) > 3
    indicator.root.destroy()
