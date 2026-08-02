#!/usr/bin/env python3
"""Unified local build script for Arcade.

Builds, for the operating system this script is run on:
    1. Frontend static bundle          (npm — frontend/)
    2. Ed25519 license keypair          (only if missing —
       tools/keygen/generate_keys.py)
    3. Launcher / server                (PyInstaller --onedir — arcade.spec)
    4. Keygen tool                      (PyInstaller —
       tools/keygen/keygen.spec, optional)
    5. Agent                            (electron-builder — agent/)

IMPORTANT: PyInstaller and electron-builder cannot cross-compile. Running this
script produces artifacts ONLY for the OS you're running it on (Windows,
macOS, or Linux) — it does not build all three OS's binaries from one
machine. Cross-platform release artifacts remain the job of the CI matrix
(.github/workflows/build.yml). This script is the "clone it and build it for
your own machine" path, not a replacement for CI releases.

Usage:
    python build.py                     # build everything
    python build.py --only launcher      # rebuild just one component
    python build.py --only launcher --only agent
    python build.py --skip-keygen        # skip the (optional) keygen app
    python build.py --no-clean           # keep previous build/dist folders
    python build.py --regenerate-keys    # force a NEW keypair (DANGEROUS —
                                          # invalidates every license issued
                                          # against the current key)
    python build.py --self-test          # run launcher/agent self-checks after
                                          # building

Adjust the CONFIGURATION block below if your repo layout differs from the
assumptions this script makes (arcade.spec at repo root, keygen.spec inside
tools/keygen/, an optional NSIS script for the Windows installer wrap, etc).
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION — adjust these if your repo layout differs
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent  # build.py sits at project root

FRONTEND_DIR = REPO_ROOT / "frontend"
AGENT_DIR = REPO_ROOT / "agent"
KEYGEN_DIR = REPO_ROOT / "tools" / "keygen"

GENERATE_KEYS_SCRIPT = KEYGEN_DIR / "generate_keys.py"
PRIVATE_KEY_PATH = KEYGEN_DIR / "private_key.pem"
PUBLIC_KEY_MODULE = REPO_ROOT / "backend" / "licensing" / "public_key.py"

ARCADE_SPEC = REPO_ROOT / "arcade.spec"
KEYGEN_SPEC = KEYGEN_DIR / "keygen.spec"

LAUNCHER_DIST = REPO_ROOT / "dist"  # PyInstaller --distpath default, run from repo root
KEYGEN_DIST = KEYGEN_DIR / "dist"  # per Epic 11.2: build dir inside tools/keygen/dist
AGENT_DIST = AGENT_DIR / "dist"  # electron-builder output

# Optional: NSIS script that wraps the launcher onedir output into a single
# Windows installer .exe. Skipped automatically if this file doesn't exist.
NSIS_SCRIPT = REPO_ROOT / "installer.nsi"

IS_WINDOWS = platform.system() == "Windows"

built_artifacts: dict[str, list[Path]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def run(
    cmd: list[str], cwd: Path, step_name: str, input_text: str | None = None
) -> None:
    """Run a subprocess, streaming its output, and abort the build on failure."""
    print(f"  $ {' '.join(cmd)}   (cwd: {cwd})")
    # On Windows, npm/node are .cmd files - use shell=True to resolve them
    use_shell = IS_WINDOWS and cmd[0] in ("npm", "node", "npx", "makensis")
    # S603: cmd is a controlled list of known commands, not user input
    result = subprocess.run(cmd, cwd=cwd, text=True, input=input_text, shell=use_shell)  # noqa: S603
    if result.returncode != 0:
        print(f"\n[FAIL] {step_name} (exit code {result.returncode})")
        sys.exit(1)


def check_tool(name: str, hint: str) -> None:
    if shutil.which(name) is None:
        print(f"[FAIL] Missing prerequisite: '{name}' not found on PATH. {hint}")
        sys.exit(1)


def snapshot(directory: Path) -> set[Path]:
    if not directory.exists():
        return set()
    return {p for p in directory.rglob("*") if p.is_file()}


def new_files_since(directory: Path, before: set[Path]) -> list[Path]:
    if not directory.exists():
        return []
    after = {p for p in directory.rglob("*") if p.is_file()}
    return sorted(after - before)


def onedir_root_for(new_files: list[Path], dist_dir: Path) -> Path:
    """Given files that newly appeared under dist_dir, find the top-level
    onedir folder PyInstaller created (dist_dir/<app_name>/...)."""
    for f in new_files:
        for parent in f.parents:
            if parent.parent == dist_dir:
                return parent
    return new_files[0]


def rmtree_retry(path: Path, max_attempts: int = 5, delay: float = 0.5) -> None:
    """Remove a directory tree with retries for Windows file locking issues."""
    for attempt in range(max_attempts):
        try:
            if path.exists():
                shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == max_attempts - 1:
                raise
            time.sleep(delay)
        except OSError:
            if attempt == max_attempts - 1:
                raise
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
def check_prerequisites(components: set[str]) -> None:
    header("Checking prerequisites")

    if "frontend" in components or "agent" in components:
        check_tool("node", "Install Node.js 20 LTS: https://nodejs.org")
        check_tool("npm", "Install Node.js 20 LTS: https://nodejs.org")

    if "launcher" in components or "keygen" in components:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print("[FAIL] PyInstaller not installed in this Python environment.")
            print("  Install it with: pip install pyinstaller==6.12.0")
            sys.exit(1)

        try:
            import nacl  # noqa: F401
        except ImportError:
            print(
                "[FAIL] PyNaCl not installed "
                "(required by generate_keys.py / licensing)."
            )
            print("  Install it with: pip install PyNaCl")
            sys.exit(1)

    # Note: makensis check moved to build_launcher() where we actually run it
    # Per TODO.md: if NSIS script doesn't exist or makensis missing, skip gracefully

    print("[OK] All required tools found.")


# ---------------------------------------------------------------------------
# Step: Ed25519 keypair
# ---------------------------------------------------------------------------
def ensure_keys(force: bool) -> None:
    header("Ed25519 license keypair")

    if not PRIVATE_KEY_PATH.exists():
        print("No private key found -- generating a fresh keypair for this clone.")
        run(
            [sys.executable, str(GENERATE_KEYS_SCRIPT)],
            cwd=REPO_ROOT,
            step_name="key generation",
        )
    elif force:
        print("WARNING: --regenerate-keys was passed.")
        print("   This creates a NEW keypair. Every license issued against the")
        print("   CURRENT key will stop verifying once the new public key is")
        print("   baked into a build.")
        confirm = input("   Type 'yes' to proceed: ").strip().lower()
        if confirm != "yes":
            print("   Aborted key regeneration -- keeping existing keypair.")
        else:
            # generate_keys.py asks its own "Continue? [y/N]" since the file
            # already exists; answer it here so this doesn't hang.
            run(
                [sys.executable, str(GENERATE_KEYS_SCRIPT)],
                cwd=REPO_ROOT,
                step_name="key regeneration",
                input_text="y\n",
            )
    else:
        print(f"[OK] Existing keypair found at {PRIVATE_KEY_PATH} -- reusing it.")

    if not PUBLIC_KEY_MODULE.exists():
        print(
            f"[FAIL] {PUBLIC_KEY_MODULE} is missing even after "
            "key generation. Aborting."
        )
        sys.exit(1)
    print(f"[OK] Public key module present at {PUBLIC_KEY_MODULE}")


# ---------------------------------------------------------------------------
# Step: frontend
# ---------------------------------------------------------------------------
def build_frontend(no_clean: bool) -> None:
    header("Building frontend (React + Vite)")
    dist = FRONTEND_DIR / "dist"
    if not no_clean and dist.exists():
        rmtree_retry(dist)

    run(["npm", "ci"], cwd=FRONTEND_DIR, step_name="frontend npm ci")
    run(["npm", "run", "build"], cwd=FRONTEND_DIR, step_name="frontend build")

    if not dist.exists():
        print(f"[FAIL] Expected {dist} after frontend build but it wasn't created.")
        sys.exit(1)

    built_artifacts["Frontend (embedded in launcher)"] = [dist]
    print(f"[OK] Frontend built -> {dist}")


# ---------------------------------------------------------------------------
# Step: launcher / server
# ---------------------------------------------------------------------------
def build_launcher(no_clean: bool) -> None:
    header("Building launcher / server (PyInstaller)")

    if not ARCADE_SPEC.exists():
        print(
            f"[FAIL] {ARCADE_SPEC} not found. "
            "Adjust ARCADE_SPEC at the top of this script."
        )
        sys.exit(1)

    if not no_clean:
        for stale in (LAUNCHER_DIST, REPO_ROOT / "build"):
            if stale.exists():
                rmtree_retry(stale)

    before = snapshot(LAUNCHER_DIST)
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(ARCADE_SPEC),
            "--clean",
            "--noconfirm",
        ],
        cwd=REPO_ROOT,
        step_name="launcher PyInstaller build",
    )
    new_files = new_files_since(LAUNCHER_DIST, before)
    if not new_files:
        # With --no-clean, PyInstaller overwrites existing files rather than
        # creating new ones. Fall back to finding the onedir folder directly.
        print(
            "  [INFO] No new files detected (likely --no-clean mode), "
            "searching for onedir output..."
        )
        onedir_candidates = [
            p
            for p in LAUNCHER_DIST.iterdir()
            if p.is_dir() and (p / "Arcade Launcher.exe").exists()
        ]
        if not onedir_candidates:
            # Try common name patterns
            onedir_candidates = [
                p
                for p in LAUNCHER_DIST.iterdir()
                if p.is_dir() and p.name.startswith("arcade")
            ]
        if onedir_candidates:
            onedir_root = onedir_candidates[0]
            print(f"  [OK] Found existing onedir output: {onedir_root}")
        else:
            print(
                f"[FAIL] PyInstaller reported success but no onedir "
                f"folder found under {LAUNCHER_DIST}."
            )
            sys.exit(1)
    else:
        onedir_root = onedir_root_for(new_files, LAUNCHER_DIST)
    artifacts = [onedir_root]

    if IS_WINDOWS and NSIS_SCRIPT.exists():
        print("Wrapping onedir output with NSIS installer...")
        before_nsis = snapshot(REPO_ROOT)
        # makensis might not be installed - handle gracefully
        try:
            run(
                ["makensis", str(NSIS_SCRIPT)],
                cwd=REPO_ROOT,
                step_name="NSIS installer build",
            )
            installer = [
                p
                for p in new_files_since(REPO_ROOT, before_nsis)
                if p.suffix.lower() == ".exe"
            ]
            artifacts.extend(installer)
        except SystemExit:
            print(
                "  [WARN] makensis not found or failed - "
                "shipping raw onedir folder instead."
            )
    elif IS_WINDOWS:
        print(
            f"  (No NSIS script at {NSIS_SCRIPT} — "
            "shipping the raw onedir folder instead.)"
        )

    built_artifacts["Launcher / server"] = artifacts
    print(f"[OK] Launcher built -> {onedir_root}")


# ---------------------------------------------------------------------------
# Step: keygen tool (optional)
# ---------------------------------------------------------------------------
def build_keygen(no_clean: bool) -> None:
    header("Building keygen tool (PyInstaller)")

    if not KEYGEN_SPEC.exists():
        print(f"  {KEYGEN_SPEC} not found - skipping (Epic 11.2 marks this optional).")
        return

    if not no_clean:
        for stale in (KEYGEN_DIST, KEYGEN_DIR / "build"):
            if stale.exists():
                rmtree_retry(stale)

    before = snapshot(KEYGEN_DIST)
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(KEYGEN_SPEC),
            "--clean",
            "--noconfirm",
        ],
        cwd=KEYGEN_DIR,
        step_name="keygen PyInstaller build",
    )
    new_files = new_files_since(KEYGEN_DIST, before)
    if not new_files:
        # With --no-clean, PyInstaller overwrites existing files rather than
        # creating new ones. Fall back to finding the onedir folder directly.
        print(
            "  [INFO] No new files detected (likely --no-clean mode), "
            "searching for onedir output..."
        )
        onedir_candidates = [
            p
            for p in KEYGEN_DIST.iterdir()
            if p.is_dir() and (p / "Arcade Keygen.exe").exists()
        ]
        if not onedir_candidates:
            onedir_candidates = [
                p
                for p in KEYGEN_DIST.iterdir()
                if p.is_dir() and p.name.startswith("arcade-keygen")
            ]
        if onedir_candidates:
            onedir_root = onedir_candidates[0]
            print(f"  [OK] Found existing onedir output: {onedir_root}")
        else:
            print(
                f"[FAIL] PyInstaller reported success but no onedir folder found "
                f"under {KEYGEN_DIST}."
            )
            sys.exit(1)
    else:
        onedir_root = onedir_root_for(new_files, KEYGEN_DIST)
    built_artifacts["Keygen tool"] = [onedir_root]
    print(f"[OK] Keygen tool built -> {onedir_root}")


# ---------------------------------------------------------------------------
# Step: agent
# ---------------------------------------------------------------------------
def build_agent(no_clean: bool) -> None:
    header("Building agent (Electron)")
    if not no_clean and AGENT_DIST.exists():
        rmtree_retry(AGENT_DIST)

    run(["npm", "ci"], cwd=AGENT_DIR, step_name="agent npm ci")
    run(
        ["npm", "run", "build"], cwd=AGENT_DIR, step_name="agent electron-builder build"
    )

    if not AGENT_DIST.exists():
        print(f"[FAIL] Expected {AGENT_DIST} after agent build but it wasn't created.")
        sys.exit(1)

    installer_exts = {".exe", ".dmg", ".zip", ".appimage", ".deb"}
    installers = [
        p
        for p in AGENT_DIST.rglob("*")
        if p.is_file() and p.suffix.lower() in installer_exts
    ]
    built_artifacts["Agent"] = installers or [AGENT_DIST]
    print(f"[OK] Agent built -> {AGENT_DIST}")


# ---------------------------------------------------------------------------
# Optional self-test hook
# ---------------------------------------------------------------------------
def run_self_tests(launcher_artifacts: list[Path], agent_artifacts: list[Path]) -> None:
    header("Self-tests")

    # Find launcher executable (PyInstaller onedir output)
    launcher_exe = None
    for artifact in launcher_artifacts:
        if artifact.is_dir():
            # Look for the .exe inside the onedir folder
            for exe in artifact.rglob("*.exe"):
                if "Arcade" in exe.name and "Launcher" in exe.name:
                    launcher_exe = exe
                    break
            if launcher_exe:
                break
        elif artifact.suffix.lower() == ".exe":
            launcher_exe = artifact
            break

    if launcher_exe and launcher_exe.exists():
        print(f"  Running launcher self-test: {launcher_exe}")
        try:
            subprocess.run(  # noqa: S603
                [str(launcher_exe), "--self-test"], check=True, cwd=launcher_exe.parent
            )
            print("  [OK] Launcher self-test passed")
        except subprocess.CalledProcessError as e:
            print(f"  [FAIL] Launcher self-test failed with exit code {e.returncode}")
            sys.exit(1)
    else:
        print("  [WARN] Launcher executable not found, skipping self-test")

    # Find agent executable/installer
    agent_exe = None
    for artifact in agent_artifacts:
        if artifact.is_dir():
            # Look for built agent executable
            for exe in artifact.rglob("*.exe"):
                if "Arcade" in exe.name and "Agent" in exe.name:
                    agent_exe = exe
                    break
            if not agent_exe:
                # macOS .app bundle
                for app in artifact.rglob("*.app"):
                    agent_exe = app
                    break
            if agent_exe:
                break
        elif artifact.suffix.lower() in {".exe", ".appimage", ".dmg", ".app"}:
            agent_exe = artifact
            break

    if agent_exe and agent_exe.exists():
        print(f"  Running agent smoke-test: {agent_exe}")
        try:
            if agent_exe.suffix.lower() == ".app":
                # macOS app bundle - run the executable inside
                mac_exe = agent_exe / "Contents" / "MacOS" / "Arcade Agent"
                if mac_exe.exists():
                    subprocess.run([str(mac_exe), "--smoke-test"], check=True)  # noqa: S603
                    print("  [OK] Agent smoke-test passed")
                else:
                    print(
                        "  [WARN] Agent .app executable not found inside bundle, "
                        "skipping"
                    )
            else:
                subprocess.run(  # noqa: S603
                    [str(agent_exe), "--smoke-test"], check=True, cwd=agent_exe.parent
                )
                print("  [OK] Agent smoke-test passed")
        except subprocess.CalledProcessError as e:
            print(f"  [FAIL] Agent smoke-test failed with exit code {e.returncode}")
            sys.exit(1)
        except FileNotFoundError:
            print("  [WARN] Agent executable not found, skipping smoke-test")
    else:
        print("  [WARN] Agent artifact not found, skipping smoke-test")


# ---------------------------------------------------------------------------
# Final manifest
# ---------------------------------------------------------------------------
def print_manifest() -> None:
    header("Build complete — artifact locations")
    if not built_artifacts:
        print("  (nothing was built)")
        return
    for label, paths in built_artifacts.items():
        print(f"\n{label}:")
        for p in paths:
            print(f"  {p}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Arcade's launcher, agent, and keygen tool for this OS."
    )
    parser.add_argument(
        "--only",
        choices=["frontend", "launcher", "agent", "keygen"],
        action="append",
        help="Build only the given component(s). Repeatable. Default: build "
        "everything. Overrides --skip-keygen.",
    )
    parser.add_argument(
        "--skip-keygen",
        action="store_true",
        help="Skip building the keygen tool. Ignored if --only is used.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Don't wipe previous build/dist folders first.",
    )
    parser.add_argument(
        "--regenerate-keys",
        action="store_true",
        help="Force a NEW Ed25519 keypair. DANGEROUS: invalidates every license "
        "issued against the current key. Requires interactive confirmation.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run launcher/agent self-tests after building.",
    )
    args = parser.parse_args()

    print(f"Arcade local build — {platform.system()} {platform.machine()}")

    if args.only:
        components = set(args.only)
    else:
        components = {"frontend", "launcher", "agent", "keygen"}
        if args.skip_keygen:
            components.discard("keygen")

    check_prerequisites(components)

    # Keys must be in place before launcher or keygen packaging, regardless of --only.
    if "launcher" in components or "keygen" in components:
        ensure_keys(force=args.regenerate_keys)

    if "frontend" in components:
        build_frontend(args.no_clean)
    elif "launcher" in components and not (FRONTEND_DIR / "dist").exists():
        print(
            "[WARN] frontend/dist is missing but the launcher needs it "
            "(arcade.spec bundles it)."
        )
        print("   Building frontend first.")
        build_frontend(args.no_clean)

    if "launcher" in components:
        build_launcher(args.no_clean)
    launcher_artifacts = built_artifacts.get("Launcher / server", [])

    if "keygen" in components:
        build_keygen(args.no_clean)

    if "agent" in components:
        build_agent(args.no_clean)
    agent_artifacts = built_artifacts.get("Agent", [])

    if args.self_test:
        run_self_tests(launcher_artifacts, agent_artifacts)

    print_manifest()


if __name__ == "__main__":
    main()
