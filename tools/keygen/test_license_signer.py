"""Guard: the signer output must stay deterministic and decodable.

The signing logic in generate_license.py is intentionally NOT modified by the
GUI redesign. This test fails loudly if that contract is broken.

The private key is internal and never committed/shipped, so the test skips
gracefully where it is absent (CI, fresh clones) instead of erroring.
"""

import base64
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_license import build_and_write_license

KEY_PATH = Path(__file__).resolve().parent / "private_key.pem"


def test_build_and_write_license_is_deterministic_and_decodable(tmp_path):
    if not KEY_PATH.exists():
        pytest.skip("internal private key absent (not committed to the repo)")

    out = tmp_path / "license.key"
    blob1 = build_and_write_license(
        hardware_id="hwid-abc",
        cafe_name="Galaxy",
        license_type="PERPETUAL",
        trial_days=None,
        output_path=str(out),
    )
    blob2 = build_and_write_license(
        hardware_id="hwid-abc",
        cafe_name="Galaxy",
        license_type="PERPETUAL",
        trial_days=None,
        output_path=str(out),
    )
    assert blob1 == blob2  # deterministic envelope

    envelope = json.loads(base64.b64decode(blob1))
    assert envelope["payload"]["hardware_id"] == "hwid-abc"
    assert envelope["payload"]["cafe_name"] == "Galaxy"
    assert "signature" in envelope
    assert out.exists()
