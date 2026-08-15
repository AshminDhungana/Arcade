# CI Artifact Upload Fix Design

## Problem
The GitHub Actions workflow `build.yml` fails at the "Upload Launcher artifact" step because it references outputs from conditional packaging steps that are skipped on other platforms. When a step is skipped, its outputs don't exist, causing the `||` fallback to yield an empty path.

## Solution: Single Cross-Platform Packaging Step

Replace the three conditional packaging steps (Windows, macOS, Linux) with one step that runs on all platforms, detects the OS, packages accordingly, and sets a single output.

### Launcher Artifact Changes

**Remove (lines 151-177):**
- `Package Launcher artifact (Windows)`
- `Package Launcher artifact (macOS)`
- `Package Launcher artifact (Linux)`

**Add (single step):**
```yaml
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

**Update upload step (line 277-282):**
```yaml
- name: Upload Launcher artifact
  uses: actions/upload-artifact@v4
  with:
    name: arcade-launcher-${{ matrix.os }}-${{ matrix.arch }}
    path: ${{ steps.package_launcher.outputs.path }}
    retention-days: 30
```

### Agent Artifact Changes

**Remove (lines 237-272):**
- `Package Agent artifacts (Windows)`
- `Package Agent artifacts (macOS)`
- `Package Agent artifacts (Linux)`

**Add (single step):**
```yaml
- name: Package Agent artifacts
  id: package_agent
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

**Update upload step (lines 284-289):**
```yaml
- name: Upload Agent artifact(s)
  uses: actions/upload-artifact@v4
  with:
    name: arcade-agent-${{ matrix.os }}-${{ matrix.arch }}
    path: ${{ steps.package_agent.outputs.paths }}
    retention-days: 30
```

## Benefits
- Single packaging step always runs → output always available
- No fallback logic with `||` needed
- Consistent pattern for both launcher and agent
- Easier to maintain and debug
- Works with `actions/upload-artifact@v4` multi-path support

## Testing
- Push to `develop` branch to trigger CI
- Verify all three matrix jobs complete and upload artifacts successfully
- Check GitHub Actions artifacts page for expected files
