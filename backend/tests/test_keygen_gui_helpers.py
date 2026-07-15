# backend/tests/test_keygen_gui_helpers.py
"""Tests for the GUI/CLI-shared helpers added to generate_license.py."""

from __future__ import annotations

import base64
import json

import pytest

from tools.keygen.generate_license import (
    KeygenError,
    build_and_write_license,
    format_verify_command,
    load_private_key,
    parse_trial_days,
)


class TestParseTrialDays:
    def test_valid_int(self) -> None:
        assert parse_trial_days("30") == 30

    def test_none_when_blank(self) -> None:
        assert parse_trial_days("") is None
        assert parse_trial_days(None) is None

    def test_raises_on_non_int(self) -> None:
        with pytest.raises(ValueError):
            parse_trial_days("abc")

    def test_raises_on_non_positive(self) -> None:
        with pytest.raises(ValueError):
            parse_trial_days("0")
        with pytest.raises(ValueError):
            parse_trial_days("-5")


class TestFormatVerifyCommand:
    def test_matches_existing_cli_text(self) -> None:
        cmd = format_verify_command("license.key")
        assert cmd == (
            'python -c "from backend.licensing.verify import check_license; '
            "print(check_license('license.key'))\""
        )


class TestBuildAndWriteLicense:
    def test_writes_verifiable_license_file(self, tmp_path, monkeypatch) -> None:
        from nacl.signing import SigningKey

        signing_key = SigningKey.generate()
        monkeypatch.setattr(
            "tools.keygen.generate_license.load_private_key",
            lambda: signing_key.encode().hex(),
        )

        out = tmp_path / "out.key"
        blob = build_and_write_license(
            hardware_id="hwid-1234567890abcdef",
            cafe_name="GUI Test Cafe",
            license_type="TRIAL",
            trial_days=14,
            output_path=str(out),
        )

        assert out.exists()
        assert out.read_text() == blob
        # Envelope is decodable and well-formed
        env = json.loads(base64.b64decode(blob))
        assert env["payload"]["cafe_name"] == "GUI Test Cafe"
        assert env["payload"]["license_type"] == "TRIAL"


class TestLoadPrivateKey:
    def test_raises_keygen_error_when_missing(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setattr(
            "tools.keygen.generate_license.PRIVATE_KEY_PATH", tmp_path / "nope.pem"
        )
        with pytest.raises(KeygenError):
            load_private_key()
