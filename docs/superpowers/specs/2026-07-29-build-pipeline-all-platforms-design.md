# Build Pipeline: All Components on All Platforms

**Date:** 2026-07-29
**Status:** Draft
**Author:** Ashmin Dhungana

---

## 1. Context & Scope

The project currently has:
- **Windows Launcher pipeline** (`.github/workflows/build-windows.yml`): Builds frontend → PyInstaller onedir → NSIS installer
- **macOS Agent pipeline** (`.github/workflows/build-agent-mac.yml`): electron-builder DMG + ZIP (x64 + arm64)
- **Linux Agent pipeline** (`.github/workflows/build-agent-linux.yml`): electron-builder AppImage + .deb (x64)

**Missing:**
- macOS Launcher pipeline
- Linux Launcher pipeline
- Unified workflow building all 3 components (Launcher, Frontend, Agent) on each platform

This spec defines a **single matrix workflow** that builds all components on all 3 platforms, with smoke-test verification per component.

---

## 2. Goals

- One workflow file (`.github/workflows/build.yml`) using `strategy.matrix` over `os: [windows-latest, macos-latest, ubuntu-latest]`
- Each job builds **all three components**: Frontend → Launcher → Agent
- Each component has a `--self-test` / `--smoke-test` CLI flag for CI verification
- Artifacts uploaded with consistent naming: `arcade-{component}-{version}-{os}-{arch}.{ext}`
- GitHub Release created on tag push with all artifacts attached

---

## 3. Non-Goals (v1)

- Code signing / notarization (macOS) — v2
- AppImage / .deb for Launcher on Linux — v2 (tarball only)
- DMG for Launcher on macOS — v2 (tarball only)
- Cross-compilation — not supported by PyInstaller / electron-builder
- Auto-update infrastructure — v2

---

## 4. Artifact Formats

| Component | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| **Launcher** | `arcade-launcher-{ver}-windows-x64.zip` (PyInstaller onedir zipped) | `arcade-launcher-{ver}-macos-{arch}.tar.gz` (PyInstaller onedir) | `arcade-launcher-{ver}-linux-x64.tar.gz` (PyInstaller onedir) |
| **Agent** | `arcade-agent-{ver}-windows-x64.exe` (NSIS) | `arcade-agent-{ver}-macos-{arch}.dmg` + `.zip` | `arcade-agent-{ver}-linux-x64.AppImage` + `.deb` |
| **Frontend** | Bundled inside Launcher (no standalone artifact) | Same | Same |

> **Rationale:** PyInstaller `--onedir` + `--windowed` produces a native `.app` bundle on macOS and a folder on Linux. Tarballing preserves symlinks (required by PyInstaller 6+). NSIS / electron-builder formats are already working for Windows/macOS/Linux Agent.
>
> **Note:** The existing `build-windows.yml` produces an NSIS installer for the Launcher. This new unified workflow replaces it with a zip artifact for consistency. The NSIS installer can be added back in v2 if needed.

---

## 5. Verification (Smoke Tests)

Each component exposes a CLI flag that runs in CI without user interaction:

### Launcher (`launcher.py --self-test`)
```python
# Pseudocode
def self_test():
    # 1. Run alembic upgrade head against bundled sqlite
    # 2. Initialize Tkinter (headless on Linux via xvfb-run)
    # 3. Verify license check logic runs (mock license.key)
    # 4. Exit 0 on success, non-zero on failure
```

### Agent (`src/main/index.ts --smoke-test`)
```typescript
// Pseudocode
async function smokeTest() {
  // 1. Launch Electron app (no window, or offscreen)
  // 2. Verify kiosk overlay component mounts (React render)
  // 3. Verify platform abstraction loads (showKioskOverlay stub)
  // 4. app.quit() with code 0/1
}
```

### Frontend
Verified implicitly: `npm run build` must succeed; output copied into Launcher `datas`.

---

## 6. Matrix Workflow Definition

### `.github/workflows/build.yml`

```yaml
name: Build All Platforms

on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      version:
        description: 'Version override (e.g., 1.0.0)'
        required: false
        type: string

permissions:
  contents: write

jobs:
  build:
    name: Build ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    timeout-minutes: 45
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: windows-latest
            artifact_ext: zip
            arch: x64
            launcher_target: onedir
            agent_target: nsis
            node_version: '22'
            python_version: '3.12'
          - os: macos-latest
            artifact_ext: tar.gz
            arch: arm64   # macos-latest is Apple Silicon
            launcher_target: onedir
            agent_target: dmg+zip
            node_version: '22'
            python_version: '3.12'
          - os: ubuntu-latest
            artifact_ext: tar.gz
            arch: x64
            launcher_target: onedir
            agent_target: appimage+deb
            node_version: '22'
            python_version: '3.12'

    env:
      PYTHON_VERSION: ${{ matrix.python_version }}
      NODE_VERSION: ${{ matrix.node_version }}
      # Version from tag (refs/tags/v1.0.0) or workflow_dispatch input
      VERSION: ${{ github.event.inputs.version || github.ref_name.replace('refs/tags/v', '') }}

    steps:
      # ---------------------------------------------------------
      # Checkout & Setup
      # ---------------------------------------------------------
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          cache-dependency-path: |
            backend/requirements.txt
            backend/requirements-dev.txt

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: |
            frontend/package-lock.json
            agent/package-lock.json

      - name: Install 7zip (Windows)
        if: runner.os == 'Windows'
        run: choco install 7zip -y

      # ---------------------------------------------------------
      # Build Frontend (required for Launcher datas)
      # ---------------------------------------------------------
      - name: Build Frontend
        working-directory: frontend
        run: |
          npm ci
          npm run build

      - name: Verify frontend/dist exists
        run: test -f frontend/dist/index.html

      # ---------------------------------------------------------
      # Build Launcher (PyInstaller)
      # ---------------------------------------------------------
      - name: Install Python dependencies (Launcher)
        working-directory: backend
        run: |
          pip install -r requirements.txt -r requirements-dev.txt pyinstaller

      - name: Build Launcher with PyInstaller
        run: |
          pyinstaller arcade.spec --clean --noconfirm

      - name: Verify Launcher bundle
        run: |
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            test -f dist/arcade/arcade.exe
          elif [ "${{ matrix.os }}" = "macos-latest" ]; then
            test -d "dist/arcade.app"
          else
            test -f dist/arcade/arcade
          fi

      - name: Smoke test Launcher
        run: |
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            dist/arcade/arcade.exe --self-test
          elif [ "${{ matrix.os }}" = "macos-latest" ]; then
            ./dist/arcade.app/Contents/MacOS/Arcade\ Launcher --self-test
          else
            xvfb-run -a ./dist/arcade/arcade --self-test
          fi

      - name: Package Launcher artifact
        id: launcher_artifact
        run: |
          VERSION="${{ env.VERSION }}"
          OS="${{ matrix.os }}"
          ARCH="${{ matrix.arch }}"
          EXT="${{ matrix.artifact_ext }}"

          if [ "$OS" = "windows-latest" ]; then
            cd dist
            "C:\Program Files\7-Zip\7z.exe" a -tzip "../arcade-launcher-${VERSION}-windows-${ARCH}.zip" arcade/*
            echo "path=../arcade-launcher-${VERSION}-windows-${ARCH}.zip" >> $GITHUB_OUTPUT
          elif [ "$OS" = "macos-latest" ]; then
            tar -czf "../arcade-launcher-${VERSION}-macos-${ARCH}.tar.gz" -C dist arcade.app
            echo "path=../arcade-launcher-${VERSION}-macos-${ARCH}.tar.gz" >> $GITHUB_OUTPUT
          else
            tar -czf "../arcade-launcher-${VERSION}-linux-${ARCH}.tar.gz" -C dist arcade
            echo "path=../arcade-launcher-${VERSION}-linux-${ARCH}.tar.gz" >> $GITHUB_OUTPUT
          fi

      # ---------------------------------------------------------
      # Build Agent (electron-builder)
      # ---------------------------------------------------------
      - name: Install Agent dependencies
        working-directory: agent
        run: npm ci

      - name: Install system deps (Linux)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y xvfb libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2

      - name: Build Agent
        working-directory: agent
        env:
          CSC_IDENTITY_AUTO_DISCOVERY: false
        run: |
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            npm run build -- --win
          elif [ "${{ matrix.os }}" = "macos-latest" ]; then
            npm run build -- --mac
          else
            npm run build -- --linux
          fi

      - name: Verify Agent artifacts
        working-directory: agent
        run: |
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            test -f dist/*.exe
          elif [ "${{ matrix.os }}" = "macos-latest" ]; then
            test -f dist/*.dmg && test -f dist/*.zip
          else
            test -f dist/*.AppImage && test -f dist/*.deb
          fi

      - name: Smoke test Agent
        working-directory: agent
        run: |
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            ./dist/arcade-agent.exe --smoke-test
          elif [ "${{ matrix.os }}" = "macos-latest" ]; then
            # Extract .app from .dmg or use the unpacked app
            ./dist/mac*/Arcade\ Agent.app/Contents/MacOS/Arcade\ Agent --smoke-test
          else
            xvfb-run -a ./dist/*.AppImage --smoke-test
          fi

      - name: Package Agent artifacts
        id: agent_artifact
        working-directory: agent
        run: |
          VERSION="${{ env.VERSION }}"
          OS="${{ matrix.os }}"
          ARCH="${{ matrix.arch }}"

          if [ "$OS" = "windows-latest" ]; then
            cp dist/*.exe ../arcade-agent-${VERSION}-windows-${ARCH}.exe
            echo "path=../arcade-agent-${VERSION}-windows-${ARCH}.exe" >> $GITHUB_OUTPUT
          elif [ "$OS" = "macos-latest" ]; then
            cp dist/*.dmg ../arcade-agent-${VERSION}-macos-${ARCH}.dmg
            cp dist/*.zip ../arcade-agent-${VERSION}-macos-${ARCH}.zip
            echo "paths<<EOF" >> $GITHUB_OUTPUT
            echo "../arcade-agent-${VERSION}-macos-${ARCH}.dmg" >> $GITHUB_OUTPUT
            echo "../arcade-agent-${VERSION}-macos-${ARCH}.zip" >> $GITHUB_OUTPUT
            echo "EOF" >> $GITHUB_OUTPUT
          else
            cp dist/*.AppImage ../arcade-agent-${VERSION}-linux-${ARCH}.AppImage
            cp dist/*.deb ../arcade-agent-${VERSION}-linux-${ARCH}.deb
            echo "paths<<EOF" >> $GITHUB_OUTPUT
            echo "../arcade-agent-${VERSION}-linux-${ARCH}.AppImage" >> $GITHUB_OUTPUT
            echo "../arcade-agent-${VERSION}-linux-${ARCH}.deb" >> $GITHUB_OUTPUT
            echo "EOF" >> $GITHUB_OUTPUT
          fi

      # ---------------------------------------------------------
      # Upload Artifacts
      # ---------------------------------------------------------
      - name: Upload Launcher artifact
        uses: actions/upload-artifact@v4
        with:
          name: arcade-launcher-${{ matrix.os }}-${{ matrix.arch }}
          path: ${{ steps.launcher_artifact.outputs.path }}
          retention-days: 30

      - name: Upload Agent artifact(s)
        uses: actions/upload-artifact@v4
        with:
          name: arcade-agent-${{ matrix.os }}-${{ matrix.arch }}
          path: ${{ steps.agent_artifact.outputs.paths }}
          retention-days: 30

      # ---------------------------------------------------------
      # GitHub Release (on tag push only)
      # ---------------------------------------------------------
      - name: Create GitHub Release
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: |
            arcade-launcher-${{ env.VERSION }}-${{ matrix.os }}-${{ matrix.arch }}.*
            arcade-agent-${{ env.VERSION }}-${{ matrix.os }}-${{ matrix.arch }}.*
          generate_release_notes: true
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # ---------------------------------------------------------
  # Release aggregation job (runs after all matrix jobs complete)
  # ---------------------------------------------------------
  release:
    name: Aggregate Release
    needs: build
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          pattern: arcade-*
          merge-multiple: true

      - name: List artifacts
        run: find artifacts -type f -name "arcade-*" | sort

      - name: Final Release (attach all)
        uses: softprops/action-gh-release@v2
        with:
          files: artifacts/arcade-*
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 7. Component Changes Required

### 7.1 Launcher (`launcher.py`)

Add `--self-test` flag:

```python
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="Run CI smoke test")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(run_self_test())

def run_self_test() -> int:
    # 1. Run migrations in-memory / temp DB
    from backend.core.startup import run_migrations
    import asyncio
    asyncio.run(run_migrations())

    # 2. Verify Tkinter can initialize (headless on Linux)
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.destroy()

    # 3. Verify license check logic (mock or use test license)
    from backend.licensing.verify import check_license
    # Uses license.key in cwd; CI provides a test fixture

    print("SELF-TEST PASSED")
    return 0
```

### 7.2 Agent (`agent/src/main/index.ts`)

Add `--smoke-test` flag:

```typescript
// In main process bootstrap
if (process.argv.includes('--smoke-test')) {
  await runSmokeTest()
  process.exit(0)
}

async function runSmokeTest() {
  // 1. Load platform abstraction
  const { PlatformService } = await import('./platform/factory')
  const platform = PlatformService.getInstance()
  assert(platform, 'PlatformService not initialized')

  // 2. Verify kiosk overlay can be created (no actual window)
  const { createKioskOverlay } = await import('./renderer/kiosk')
  // Just verify the module loads and exports the component
  assert(typeof createKioskOverlay === 'function', 'Kiosk overlay not exported')

  // 3. Verify local storage (better-sqlite3) opens
  const { SessionStore } = await import('./storage/session_store')
  const store = new SessionStore(':memory:')
  store.close()

  console.log('SMOKE TEST PASSED')
}
```

### 7.3 Agent Build Script (`agent/package.json`)

The existing `npm run build` script needs to accept platform flags:

```json
{
  "scripts": {
    "build": "tsc -p tsconfig.main.json && tsc -p tsconfig.renderer.json && node scripts/copy-renderer-assets.mjs && electron-builder",
    "build:win": "npm run build -- --win",
    "build:mac": "npm run build -- --mac",
    "build:linux": "npm run build -- --linux"
  }
}
```

The workflow calls `npm run build -- --win` / `--mac` / `--linux` which passes flags to `electron-builder`.

### 7.4 PyInstaller Spec (`arcade.spec`)

Ensure `--onedir` + `--windowed` produces `.app` on macOS:

```python
# In EXE() call:
console=False,          # --windowed
target_arch=None,       # native
codesign_identity=None, # unsigned v1
```

---

## 8. CI Environment Requirements

| Platform | Additional Tools |
|----------|------------------|
| **Windows** | NSIS (already in `build-windows.yml`), 7zip (for zipping onedir) |
| **macOS** | `create-dmg` (optional, v2), Xcode CLI tools (default) |
| **Linux** | `xvfb-run` (for headless Tkinter + Electron), `appimagetool` + `fpm` (v2 only) |

Install in workflow:
```yaml
- name: Install system deps (Linux)
  if: runner.os == 'Linux'
  run: |
    sudo apt-get update
    sudo apt-get install -y xvfb libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
```

---

## 9. Versioning

- Version sourced from `pyproject.toml` → `project.version`
- GitHub tag `v{version}` triggers release
- `workflow_dispatch` input `version` overrides for manual builds

---

## 10. Rollback / Recovery

- All matrix jobs independent; failure on one OS doesn't block others
- Artifacts retained 30 days for debugging
- Re-run workflow from Actions tab with same tag (force-push tag) to rebuild

---

## 11. Acceptance Criteria

- [ ] `build.yml` workflow runs on `push: tags: v*` and `workflow_dispatch`
- [ ] Matrix completes on all 3 OSes (Windows, macOS, Linux)
- [ ] Launcher builds: onedir bundle + tarball/zip artifact
- [ ] Launcher `--self-test` passes (alembic, Tkinter, license check)
- [ ] Agent builds: NSIS / DMG+ZIP / AppImage+.deb
- [ ] Agent `--smoke-test` passes (Electron launches, kiosk overlay loads, storage works)
- [ ] GitHub Release created with all 6+ artifacts attached
- [ ] Manual verification: download Launcher tarball on clean VM, extract, run → license screen appears

---

## 12. Future Enhancements (v2+)

- Code signing + notarization (macOS)
- Code signing (Windows)
- AppImage / .deb for Launcher on Linux
- DMG for Launcher on macOS
- Auto-update (Sparkle / electron-updater)
- SBOM generation (Syft)
- SLSA provenance
