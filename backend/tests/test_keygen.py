"""Tests for tools.keygen.generate_license.

Covers the core signing function: PERPETUAL and TRIAL license generation,
payload structure, canonical JSON signing, and signature validity.
"""

from __future__ import annotations

import base64
import json
from datetime import date, timedelta

from nacl.signing import SigningKey

from tools.keygen.generate_license import generate_license


class TestGenerateLicense:
    def test_generates_valid_perpetual_license(self) -> None:
        signing_key = SigningKey.generate()
        private_hex = signing_key.encode().hex()
        hardware_id = "a" * 32

        blob = generate_license(
            private_key_hex=private_hex,
            hardware_id=hardware_id,
            cafe_name="Galaxy Gaming Lounge",
            license_type="PERPETUAL",
        )

        # Decode and inspect envelope
        raw = base64.b64decode(blob)
        envelope = json.loads(raw)
        payload = envelope["payload"]
        signature_b64 = envelope["signature"]

        # Payload content
        assert payload["cafe_name"] == "Galaxy Gaming Lounge"
        assert payload["hardware_id"] == hardware_id
        assert payload["license_type"] == "PERPETUAL"
        assert payload["issue_date"] == date.today().isoformat()
        assert payload["trial_expires_at"] is None

        # Signature is valid base64
        assert base64.b64decode(signature_b64)  # does not raise

    def test_generates_valid_trial_license(self) -> None:
        signing_key = SigningKey.generate()
        private_hex = signing_key.encode().hex()
        hardware_id = "b" * 32

        blob = generate_license(
            private_key_hex=private_hex,
            hardware_id=hardware_id,
            cafe_name="Test Cafe",
            license_type="TRIAL",
            trial_days=30,
        )

        raw = base64.b64decode(blob)
        envelope = json.loads(raw)
        payload = envelope["payload"]

        assert payload["license_type"] == "TRIAL"
        assert payload["trial_expires_at"] is not None
        expected = (date.today() + timedelta(days=30)).isoformat()
        assert payload["trial_expires_at"] == expected

    def test_signature_verifies_with_matching_public_key(self) -> None:
        """The Ed25519 signature should be verifiable with the matching public key."""
        signing_key = SigningKey.generate()
        private_hex = signing_key.encode().hex()
        hardware_id = "c" * 32

        blob = generate_license(
            private_key_hex=private_hex,
            hardware_id=hardware_id,
            cafe_name="Signature Test",
            license_type="PERPETUAL",
        )

        # Decode envelope
        raw = base64.b64decode(blob)
        envelope = json.loads(raw)
        payload = envelope["payload"]
        signature = base64.b64decode(envelope["signature"])

        # Re-canonicalize and verify with public key
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        public_key = signing_key.verify_key
        public_key.verify(canonical, signature)  # does not raise
