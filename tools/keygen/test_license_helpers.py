"""Unit tests for display-free keygen helpers."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from license_helpers import resolve_logo_path, validate_inputs


def test_resolve_logo_path_finds_committed_png():
    p = resolve_logo_path()
    assert p is None or (isinstance(p, Path) and p.name == "arcade_logo_64.png")


def test_validate_inputs_accepts_valid_perpetual():
    assert validate_inputs("abc123", "Galaxy Lounge", "PERPETUAL", None) == {}


def test_validate_inputs_accepts_valid_trial():
    assert validate_inputs("abc123", "Galaxy Lounge", "TRIAL", 30) == {}


def test_validate_inputs_rejects_empty_required():
    errs = validate_inputs("", "  ", "PERPETUAL", None)
    assert "hardware_id" in errs
    assert "cafe_name" in errs


def test_validate_inputs_rejects_bad_trial_days():
    errs = validate_inputs("abc", "Cafe", "TRIAL", "x")
    assert "trial_days" in errs
    errs2 = validate_inputs("abc", "Cafe", "TRIAL", 0)
    assert "trial_days" in errs2


def test_validate_inputs_ignores_trial_days_for_perpetual():
    # Garbage trial value is irrelevant when type is PERPETUAL.
    assert validate_inputs("abc", "Cafe", "PERPETUAL", "not-a-number") == {}
