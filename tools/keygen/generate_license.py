"""Offline license key generation tool. INTERNAL USE ONLY.

Reads the Ed25519 private key from tools/keygen/private_key.pem and produces a
signed license.key file that can be validated by the Arcade launcher.

Usage:
    python -m tools.keygen.generate_license --hardware-id <id> --cafe-name <name>
"""

from __future__ import annotations

import argparse
import base64
import json
from datetime import date, timedelta
from pathlib import Path

from nacl.signing import SigningKey

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_KEY_PATH = REPO_ROOT / "tools" / "keygen" / "private_key.pem"


class KeygenError(Exception):
    """Raised for user-facing keygen failures (e.g. missing private key)."""


def load_private_key() -> str:
    """Load the Ed25519 private key hex from private_key.pem.

    Raises:
        KeygenError: if the private key file is missing.
    """
    if not PRIVATE_KEY_PATH.exists():
        raise KeygenError(
            f"Private key not found at {PRIVATE_KEY_PATH}. "
            "Run `python -m tools.keygen.generate_keys` first."
        )
    return PRIVATE_KEY_PATH.read_text().strip()


def generate_license(
    private_key_hex: str,
    hardware_id: str,
    cafe_name: str,
    license_type: str = "PERPETUAL",
    trial_days: int | None = None,
) -> str:
    """Sign and envelope a license payload. Returns base64-encoded license string."""
    issue_date = date.today().isoformat()

    trial_expires_at: str | None = None
    if license_type == "TRIAL" and trial_days is not None:
        trial_expires_at = (date.today() + timedelta(days=trial_days)).isoformat()

    payload = {
        "cafe_name": cafe_name,
        "hardware_id": hardware_id,
        "license_type": license_type,
        "issue_date": issue_date,
        "trial_expires_at": trial_expires_at,
    }

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signing_key = SigningKey(bytes.fromhex(private_key_hex))
    signature = signing_key.sign(canonical).signature

    envelope = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode(),
    }
    return base64.b64encode(json.dumps(envelope).encode()).decode()


def parse_trial_days(value: str | None) -> int | None:
    """Parse a trial-days field from UI/CLI text.

    Blank/None -> None (PERPETUAL). Otherwise must be a positive int.

    Raises:
        ValueError: if the value is non-numeric or not positive.
    """
    if value is None or value.strip() == "":
        return None
    days = int(value)  # raises ValueError on non-numeric
    if days <= 0:
        raise ValueError("trial_days must be a positive integer")
    return days


def format_verify_command(output_path: str | Path) -> str:
    """Return the CLI verify command string (unchanged text for backward compat)."""
    return (
        f'python -c "from backend.licensing.verify import check_license; '
        f"print(check_license('{output_path}'))\""
    )


def build_and_write_license(
    hardware_id: str,
    cafe_name: str,
    license_type: str = "PERPETUAL",
    trial_days: int | None = None,
    output_path: str | Path = "license.key",
) -> str:
    """Load the private key, sign a license, and write it to ``output_path``.

    Returns the base64-encoded license blob. Shared by the CLI and GUI so
    both produce identical, verifiable licenses.

    Raises:
        KeygenError: if the private key is missing.
    """
    private_key_hex = load_private_key()
    blob = generate_license(
        private_key_hex=private_key_hex,
        hardware_id=hardware_id,
        cafe_name=cafe_name,
        license_type=license_type,
        trial_days=trial_days,
    )
    Path(output_path).write_text(blob, encoding="utf-8")
    return blob


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an offline Arcade license key"
    )
    parser.add_argument(
        "--hardware-id", required=True, help="Hardware ID of the target machine"
    )
    parser.add_argument("--cafe-name", required=True, help="Name of the cafe")
    parser.add_argument(
        "--license-type", choices=["PERPETUAL", "TRIAL"], default="PERPETUAL"
    )
    parser.add_argument(
        "--trial-days", type=int, default=30, help="Days for trial license"
    )
    args = parser.parse_args()

    private_key_hex = load_private_key()
    blob = generate_license(
        private_key_hex,
        args.hardware_id,
        args.cafe_name,
        license_type=args.license_type,
        trial_days=args.trial_days,
    )

    output_path = Path("license.key")
    output_path.write_text(blob)

    print(f"License written to: {output_path.resolve()}")
    print(f"  Cafe:     {args.cafe_name}")
    print(f"  HWID:     {args.hardware_id}")
    print(f"  Type:     {args.license_type}")
    print(f"  Trial:    {args.trial_days} days")
    print(
        f'  Verified: python -c "from backend.licensing.verify import check_license; '
        f"print(check_license('{output_path}'))\"",
    )


if __name__ == "__main__":
    main()
