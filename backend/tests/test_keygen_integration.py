"""End-to-end: generate_license() output is accepted by check_license().

Verifies that a license produced by the keygen tool is accepted by the
verification module when the keypair and hardware ID match.
"""

from __future__ import annotations

from pathlib import Path

import backend.licensing.verify as _verify_module
from backend.licensing.verify import check_license
from tools.keygen.generate_license import generate_license


def test_generated_license_passes_verification(tmp_path: Path) -> None:
    """A license produced by generate_license() must verify with check_license()."""
    from nacl.signing import SigningKey

    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()

    # Patch verify.py to use the same keypair
    original_pubkey = _verify_module.ARCADE_PUBLIC_KEY_HEX
    original_get_hwid = _verify_module.get_hardware_id
    _verify_module.ARCADE_PUBLIC_KEY_HEX = public_hex
    _verify_module.get_hardware_id = lambda: "hwid-match-123456789012"  # noqa: S105

    try:
        blob = generate_license(
            private_key_hex=private_hex,
            hardware_id="hwid-match-123456789012",
            cafe_name="E2E Test Cafe",
            license_type="PERPETUAL",
        )

        license_file = tmp_path / "license.key"
        license_file.write_text(blob)

        result = check_license(str(license_file))
        assert result.ok is True, f"Expected ok=True, got error={result.error}"
        assert result.payload is not None
        assert result.payload["cafe_name"] == "E2E Test Cafe"
    finally:
        _verify_module.ARCADE_PUBLIC_KEY_HEX = original_pubkey
        _verify_module.get_hardware_id = original_get_hwid
