"""Edge cases for the keygen tool."""

from __future__ import annotations

import base64
import json

import pytest
from nacl.signing import SigningKey

from tools.keygen.generate_license import generate_license


class TestGenerateLicenseEdgeCases:
    def test_invalid_private_key_raises(self) -> None:
        """A non-hex private key should raise ValueError."""
        with pytest.raises(ValueError):
            generate_license(
                private_key_hex="not-a-valid-hex-string",
                hardware_id="a" * 32,
                cafe_name="Test",
            )

    def test_empty_hardware_id_still_works(self) -> None:
        """Empty hardware ID is still signable (enforced by verify, not keygen)."""
        signing_key = SigningKey.generate()
        blob = generate_license(
            private_key_hex=signing_key.encode().hex(),
            hardware_id="",
            cafe_name="Test",
        )
        envelope = json.loads(base64.b64decode(blob))
        assert envelope["payload"]["hardware_id"] == ""

    def test_trial_days_none_for_perpetual(self) -> None:
        """PERPETUAL license should not set trial_expires_at."""
        signing_key = SigningKey.generate()
        blob = generate_license(
            private_key_hex=signing_key.encode().hex(),
            hardware_id="a" * 32,
            cafe_name="Test",
            license_type="PERPETUAL",
            trial_days=30,  # should be ignored for PERPETUAL
        )
        envelope = json.loads(base64.b64decode(blob))
        assert envelope["payload"]["trial_expires_at"] is None
