# CI Artifact Upload Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the GitHub Actions workflow build.yml to resolve the artifact upload failure caused by conditional step outputs being unavailable when skipped.

**Architecture:** Replace three platform-specific packaging steps (Windows, macOS, Linux) with single cross-platform packaging steps that always run and produce outputs. Apply the same pattern to both Launcher and Agent artifacts.

**Tech Stack:** GitHub Actions, bash scripting, 7-Zip (Windows), tar (macOS/Linux)

## Global Constraints

- Must work on all three platforms: Windows (windows-latest), macOS (macos-latest), Linux (ubuntu-latest)
- Use `RUNNER_OS` environment variable for platform detection
- Use matrix variables: `VERSION`, `ARCH` from env/matrix
- Output artifact names must match existing pattern: `arcade-launcher-${VERSION}-${OS}-${ARCH}.ext`
- Use `actions/upload-artifact@v4` with multi-path support for Agent artifacts
- Preserve existing retention-days: 30

---

### Task 1: Replace Launcher Packaging Steps with Single Cross-Platform Step

**Files:**
- Modify: `.github/workflows/build.yml:151-177` (remove three packaging steps)
- Modify: `.github/workflows/build.yml:151` (add single packaging step)
- Modify: `.github/workflows/build.yml:277-282` (update upload step to use single output)

**Interfaces:**
- Consumes: `env.VERSION`, `matrix.arch`, `RUNNER_OS`
- Produces: `steps.package_launcher.outputs.path` (single artifact path)

- [ ] **Step 1: Write the failing test** (verify current failure)

```bash
# Push a test commit to trigger CI and confirm the upload failure
# Expected: "Input required and not supplied: path" error on upload-artifact step
```

- [ ] **Step 2: Remove the three conditional launcher packaging steps**

```yaml
# Remove lines 151-177 (these three steps):
# - name: Package Launcher artifact (Windows)
# - name: Package Launcher artifact (macOS)
# - name: Package Launcher artifact (Linux)
```

- [ ] **Step 3: Add single cross-platform launcher packaging step**

```yaml
# Insert at line 151 (after "Verify Launcher bundle (Linux)" step):
      - name: Package Launcher artifact
        id: package_launcher
        shell: bash
        run: |
          VERSION="${{ env.VERSION }}"
          ARCH="${{ matrix.arch }}"

          if [[ "$RUNNER_OS" == "Windows" ]]; then
            "/c/Program Files/7-Zip/7z.exe" a -tzip "arcade-launcher-${VERSION}-windows-${ARCH}.zip" dist/arcade/*
            echo "path=arcade-launcher-${VERSION}-windows-${ARCH}.zip" >> "$GITHUB_OUTPUT"
          elif [[ "$RUNNER_OS" == "macOS" ]]; then
            tar -czf "arcade-launcher-${VERSION}-macos-${ARCH}.tar.gz" -C dist arcade
            echo "path=arcade-launcher-${VERSION}-macos-${ARCH}.tar.gz" >> "$GITHUB_OUTPUT"
          else
            tar -czf "arcade-launcher-${VERSION}-linux-${ARCH}.tar.gz" -C dist arcade
            echo "path=arcade-launcher-${VERSION}-linux-${ARCH}.tar.gz" >> "$GITHUB_OUTPUT"
          fi
```

- [ ] **Step 4: Update Upload Launcher artifact step to use single output**

```yaml
# Modify lines 277-282:
      - name: Upload Launcher artifact
        uses: actions/upload-artifact@v4
        with:
          name: arcade-launcher-${{ matrix.os }}-${{ matrix.arch }}
          path: ${{ steps.package_launcher.outputs.path }}
          retention-days: 30
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: replace launcher packaging with single cross-platform step"
```

---

### Task 2: Replace Agent Packaging Steps with Single Cross-Platform Step

**Files:**
- Modify: `.github/workflows/build.yml:237-272` (remove three packaging steps)
- Modify: `.github/workflows/build.yml:237` (add single packaging step)
- Modify: `.github/workflows/build.yml:284-289` (update upload step to use single output)

**Interfaces:**
- Consumes: `env.VERSION`, `matrix.arch`, `RUNNER_OS`
- Produces: `steps.package_agent.outputs.paths` (newline-separated artifact paths)

- [ ] **Step 1: Remove the three conditional agent packaging steps**

```yaml
# Remove lines 237-272 (these three steps):
# - name: Package Agent artifacts (Windows)
# - name: Package Agent artifacts (macOS)
# - name: Package Agent artifacts (Linux)
```

- [ ] **Step 2: Add single cross-platform agent packaging step**

```yaml
# Insert at line 237 (after "Verify Agent artifacts (Linux)" step):
      - name: Package Agent artifacts
        id: package_agent
        working-directory: agent
        shell: bash
        run: |
          VERSION="${{ env.VERSION }}"
          ARCH="${{ matrix.arch }}"

          if [[ "$RUNNER_OS" == "Windows" ]]; then
            cp dist/*.exe "arcade-agent-${VERSION}-windows-${ARCH}.exe"
            echo "paths=agent/arcade-agent-${VERSION}-windows-${ARCH}.exe" >> "$GITHUB_OUTPUT"
          elif [[ "$RUNNER_OS" == "macOS" ]]; then
            cp dist/*.dmg "arcade-agent-${VERSION}-macos-${ARCH}.dmg"
            echo "paths=agent/arcade-agent-${VERSION}-macos-${ARCH}.dmg" >> "$GITHUB_OUTPUT"
          else
            cp dist/*.AppImage "arcade-agent-${VERSION}-linux-${ARCH}.AppImage"
            cp dist/*.deb "arcade-agent-${VERSION}-linux-${ARCH}.deb"
            echo "paths=agent/arcade-agent-${VERSION}-linux-${ARCH}.AppImage
agent/arcade-agent-${VERSION}-linux-${ARCH}.deb" >> "$GITHUB_OUTPUT"
          fi
```

- [ ] **Step 3: Update Upload Agent artifact step to use single output**

```yaml
# Modify lines 284-289:
      - name: Upload Agent artifact(s)
        uses: actions/upload-artifact@v4
        with:
          name: arcade-agent-${{ matrix.os }}-${{ matrix.arch }}
          path: ${{ steps.package_agent.outputs.paths }}
          retention-days: 30
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: replace agent packaging with single cross-platform step"
```

---

### Task 3: Verify Fix Works on All Platforms

**Files:**
- Test: Push to `develop` branch to trigger CI

**Interfaces:**
- Consumes: All changes from Task 1 and Task 2
- Produces: Successful CI run with artifacts uploaded on all three platforms

- [ ] **Step 1: Push changes to develop branch**

```bash
git push origin develop
```

- [ ] **Step 2: Monitor GitHub Actions workflow**

```bash
# Watch workflow at: https://github.com/<owner>/<repo>/actions/workflows/build.yml
# Expected: All three matrix jobs (windows-latest, macos-latest, ubuntu-latest) complete successfully
# Verify artifacts appear in workflow run summary
```

- [ ] **Step 3: Verify artifact contents**

```bash
# Download artifacts from each platform job
# Verify:
# - Windows: arcade-launcher-<version>-windows-x64.zip contains dist/arcade/*
# - macOS: arcade-launcher-<version>-macos-arm64.tar.gz contains arcade/*
# - Linux: arcade-launcher-<version>-linux-x64.tar.gz contains arcade/*
# - Agent artifacts match expected patterns per platform
```

- [ ] **Step 4: Test tag push triggers release**

```bash
git tag v1.0.1
git push origin v1.0.1
# Verify release is created with all 6 artifacts (3 launcher + 3 agent)
```

- [ ] **Step 5: Commit final verification**

```bash
git add .github/workflows/build.yml
git commit -m "ci: verify artifact upload fix works on all platforms"
```

---

## Self-Review Checklist

- [ ] Spec coverage: All three platform packaging steps replaced for both launcher and agent
- [ ] Placeholder scan: No TBD/TODO - all code blocks are complete
- [ ] Type consistency: Output variable names match (`package_launcher`, `package_agent`)
- [ ] Cross-platform: Uses `RUNNER_OS` detection, preserves artifact naming patterns
- [ ] Release job: Uses `actions/download-artifact@v4` with pattern matching - unchanged, should work

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-15-ci-artifact-upload-fix.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
