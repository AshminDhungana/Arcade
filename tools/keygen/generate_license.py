"""Offline license key generation tool.

INTERNAL USE ONLY - Never commit private_key.pem to VCS.

Usage:
    python -m tools.keygen.generate_license --hardware-id <id>

This script reads the Ed25519 private key from private_key.pem and produces
a signed license.key file that can be validated by the Arcade launcher.
"""

import argparse


def main() -> None:
    """Generate an offline Arcade license key."""
    parser = argparse.ArgumentParser(
        description="Generate an offline Arcade license key",
    )
    parser.add_argument(
        "--hardware-id",
        required=True,
        help="Hardware ID of the target machine",
    )
    parser.add_argument(
        "--cafe-name",
        required=True,
        help="Name of the cafe",
    )
    parser.add_argument(
        "--license-type",
        choices=["PERPETUAL", "TRIAL"],
        default="PERPETUAL",
    )
    parser.add_argument(
        "--trial-days",
        type=int,
        default=30,
        help="Days for trial license",
    )
    args = parser.parse_args()

    # TODO: Implement Ed25519 signing using nacl
    print("TODO: Implement license generation")
    print(f"Hardware ID: {args.hardware_id}")
    print(f"Cafe: {args.cafe_name}")
    print(f"Type: {args.license_type}")


if __name__ == "__main__":
    main()
