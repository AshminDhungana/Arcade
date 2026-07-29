# tests/test_launcher_self_test.py
import subprocess
import sys
from pathlib import Path


def test_launcher_self_test_flag_exists() -> None:
    """--self-test flag should be recognized and exit with code 0 or 1."""
    result = subprocess.run(
        [sys.executable, "launcher.py", "--self-test"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        timeout=30,
        shell=False,
    )
    assert result.returncode in (0, 1), f"Unexpected exit code: {result.returncode}"
    assert "SELF-TEST" in result.stdout or "SELF-TEST" in result.stderr


def test_launcher_self_test_runs_migrations(monkeypatch) -> None:
    """Self-test should call run_migrations()."""

    called = {"migrations": False}

    async def mock_migrations() -> None:
        called["migrations"] = True

    monkeypatch.setattr("backend.core.startup.run_migrations", mock_migrations)

    import launcher
    from backend.licensing.verify import LicenseResult

    monkeypatch.setattr(
        "backend.licensing.verify.check_license",
        lambda: LicenseResult(
            ok=True,
            payload={
                "cafe_name": "Test",
                "hardware_id": "test",
                "license_type": "full",
                "issue_date": "2024-01-01",
            },
            error=None,
        ),
    )

    exit_code = launcher.run_self_test()
    assert exit_code == 0
    assert called["migrations"]
