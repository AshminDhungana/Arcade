"""Robust rebuild helper for the ARCH-03 PoC bundle.

Why this exists: on Windows, `pyinstaller --clean` intermittently dies with
``PermissionError: [WinError 32] ... dist`` because a previous run's handle
(aiosqlite connection pool, dllhost thumbnail generation, or Defender
on-access scan) briefly holds a file in ``dist/``. This helper:

  1. Removes ``build/`` and ``dist/`` with a retry loop that absorbs the
     transient locks (the single most common cause of repeated WinError 32).
  2. Then invokes PyInstaller on ``arch03.spec``.

Run from this directory:
    python build.py            # rebuild
    python build.py --run      # rebuild then run the frozen --self-test
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def _rmtree_retry(path: Path, attempts: int = 8, delay: float = 1.0) -> None:
    if not path.exists():
        return
    for i in range(1, attempts + 1):
        try:
            shutil.rmtree(path)
            print(f"  removed {path.name}/")
            return
        except PermissionError as exc:
            print(f"  [{i}/{attempts}] {path.name}/ locked ({exc.errno}), retrying in {delay}s…")
            time.sleep(delay)
    # Last attempt failed: surface a clear message rather than crashing the build.
    print(f"  WARNING: could not remove {path} after {attempts} attempts —")
    print("           a process is still holding a file. Close Explorer/AV and retry.")
    raise SystemExit(1)


def main() -> int:
    run_selftest = "--run" in sys.argv
    print("Cleaning previous build artifacts (transient-lock tolerant)…")
    _rmtree_retry(ROOT / "build")
    _rmtree_retry(ROOT / "dist")

    print("Building bundle with PyInstaller --onedir…")
    rc = subprocess.call([PY, "-m", "PyInstaller", "arch03.spec", "--noconfirm"], cwd=str(ROOT))
    if rc != 0:
        print(f"PyInstaller failed (exit {rc}).")
        return rc

    exe = ROOT / "dist" / "arch03_launcher" / "arch03_launcher.exe"
    print(f"\nBuild complete -> {exe}")
    if not exe.exists():
        print("Expected exe not found; aborting.")
        return 1

    if run_selftest:
        print("\nRunning frozen --self-test…")
        rc = subprocess.call([str(exe), "--self-test"], cwd=str(exe.parent))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
