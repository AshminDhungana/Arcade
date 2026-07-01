"""Tests for backend.licensing.fingerprint.

Scenarios:
1. get_hardware_id returns a 32-character hex string.
2. get_hardware_id is idempotent (same value within a process).
3. get_hardware_id respects ARCADE_TEST_HWID env override.
4. get_hardware_id works when machineid.id() is empty (fallback path).
5. _build_fallback produces non-empty output from hostname + MAC.
"""

from __future__ import annotations

import platform
from unittest.mock import patch

import pytest

from backend.licensing.fingerprint import _build_fallback, get_hardware_id

# ---------------------------------------------------------------------------
# Case 1: basic structure
# ---------------------------------------------------------------------------


class TestGetHardwareId:
    def test_returns_32_hex_chars(self) -> None:
        result = get_hardware_id()
        assert len(result) == 32
        assert all(c in "0123456789abcdef" for c in result)

    def test_idempotent(self) -> None:
        first = get_hardware_id()
        second = get_hardware_id()
        assert first == second

    def test_respects_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ARCADE_TEST_HWID", "a" * 32)
        assert get_hardware_id() == "a" * 32
        monkeypatch.delenv("ARCADE_TEST_HWID", raising=False)

    def test_fallback_path(self) -> None:
        """When machineid.id() returns empty, fallback still produces 32-hex."""
        with patch("backend.licensing.fingerprint.machineid.id", return_value=""):
            result = get_hardware_id()
            assert len(result) == 32
            assert all(c in "0123456789abcdef" for c in result)

    def test_build_fallback_includes_hostname(self) -> None:
        """The fallback always includes the hostname, so it is non-empty."""
        result = _build_fallback()
        assert result  # non-empty
        assert platform.node() in result
