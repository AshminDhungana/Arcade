"""ARCH-05 validation tests.

Each case drives check_license() to a specific LicenseResult outcome or
tamper-rejection, mirroring SDD §16.6 and FR-LIC-007/008. Cases are built out
in Tasks 5-7; this placeholder only proves pytest discovery works.
"""


def test_discovery_smoke():
    """Proves pytest discovers this package before any real code exists."""
    assert True
