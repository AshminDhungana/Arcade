"""Hardware fingerprinting for offline license binding.

Implements SDD §16.3: primary source is py-machineid; per-OS fallbacks
are used only when py-machineid returns an empty string.
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import uuid
from typing import Final

import machineid  # py-machineid (validated by ARCH-05)

# Sentinel: if set, returned verbatim (for deterministic tests + diagnostics).
_ENV_OVERRIDE: Final[str] = "ARCADE_TEST_HWID"


def get_hardware_id() -> str:
    """Return a stable 32-hex Hardware ID.

    Primary: py-machineid (works without admin on Windows/macOS/Linux).
    Fallback chain (only if py-machineid returns an empty string):
      1. OS-specific commands (wmic / system_profiler / dmidecode)
      2. hostname + first MAC address
    """
    override = os.environ.get(_ENV_OVERRIDE)
    if override:
        return override

    primary = machineid.id()
    if primary:
        raw = f"py-machineid:{primary}"
    else:
        raw = _build_fallback()

    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Fallback helpers
# ---------------------------------------------------------------------------


def _build_fallback() -> str:
    """Gather OS identifiers. Never fails: uses whatever is available."""
    fallback_parts: list[str] = []

    system = platform.system()
    if system == "Windows":
        baseboard = _wmic("baseboard", "serialnumber")
        disk = _wmic("diskdrive", "serialnumber", index=0)
        fallback_parts.extend([baseboard, disk])
    elif system == "Darwin":
        serial = _osx_system_profiler("SPHardwareDataType", "Serial Number")
        fallback_parts.append(serial)
    else:  # Linux
        baseboard = _linux_dmidecode("board_serial")
        fallback_parts.append(baseboard)

    # Ultimate fallback: hostname + MAC (always available)
    fallback_parts.append(platform.node())
    fallback_parts.append(str(uuid.getnode()))

    # Keep only non-empty parts; join into a single string
    filtered = [p for p in fallback_parts if p and p.strip()]
    return "|".join(filtered)


def _wmic(classname: str, fields: str, *, index: int | None = None) -> str:
    """Query WMIC and return the first non-empty line."""
    cmd = ["wmic", classname]
    if index is not None:
        cmd.append(f"WHERE Index={index}")
    cmd.append(f"GET {fields} /FORMAT:CSV")
    return _run_first_line(cmd)


def _osx_system_profiler(datatype: str, field: str) -> str:
    """Run system_profiler and grep for a field."""
    result = subprocess.run(  # noqa: S603
        ["system_profiler", datatype, "-detailLevel", "mini"],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode == 0 and field in result.stdout:
        for line in result.stdout.splitlines():
            if field in line:
                return line.split(":")[-1].strip()
    return ""


def _linux_dmidecode(field: str) -> str:
    """Try dmidecode, return the matching field."""
    result = subprocess.run(  # noqa: S603
        ["dmidecode", "-s", field],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip().split("\n")[-1].strip()
    return ""


def _run_first_line(cmd: list[str]) -> str:
    """Run a command and return the first non-empty line of stdout."""
    try:
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, timeout=5, check=False
        )
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if stripped:
                    return stripped
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""
