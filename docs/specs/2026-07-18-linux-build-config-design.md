# Epic 7.2 — Linux Build Configuration & Autostart Docs

- **Date:** 2026-07-18
- **Epic:** 7.2 Linux Platform Implementation (ENG-B) — build & autostart sub-task
- **Component:** `agent/` (Electron agent packaging), `docs/`, `.github/workflows/`
- **Status:** Design approved — pending implementation plan
- **Source docs:** `docs/TODO.md` (Epic 7.2), `docs/agent-setup.md`, `agent/electron-builder.yml`, `agent/src/main/platform/linux.ts`, `docs/specs/2026-07-18-macos-platform-design.md`

## Goal

Complete the Linux build-configuration task from `docs/TODO.md` (Epic 7.2):

- Confirm the `electron-builder.yml` Linux targets (already present).
- Provide operator-facing autostart artifacts: `docs/autostart/arcade-agent.desktop`
  (XDG autostart reference) and `docs/autostart/arcade-agent.service` (systemd).
- Add a Linux build CI workflow so the AppImage + `.deb` build is actually verified
  (it cannot be built on the Windows dev host).

## Context & current state

Discoveries from exploration that shape this design:

1. **`electron-builder.yml` already contains the exact Linux block** required by the
   task (lines 31–35):
   ```yaml
   linux:
     target:
       - AppImage
       - deb
     category: Utility
   ```
   No change needed there. The task sub-item is effectively already satisfied.

2. **`agent/src/main/platform/linux.ts` already auto-writes the XDG autostart file**
   at runtime when auto-start is toggled from the dashboard:
   ```ts
   const desktopEntry = [
     '[Desktop Entry]',
     'Type=Application',
     'Name=Arcade Agent',
     `Exec=${process.execPath}`,
     'X-GNOME-Autostart-enabled=true',
     'X-GNOME-Autostart-Delay=5',
     '',
   ].join('\n');
   // writes to ~/.config/autostart/arcade-agent.desktop
   ```
   So the agent is the single writer of the *runtime* file. The doc `.desktop` is a
   **reference/template** for operators, not a file the agent copies.

3. **No Linux build exists in CI.** Only `build-agent-mac.yml` (macOS) and a
   lint-only `ci.yml`. electron-builder **cannot cross-compile Linux from a Windows
   host**, so `npm run build -- --linux` is impossible on the dev box and must be
   verified on a Linux runner.

4. **`docs/agent-setup.md` already documents** the Linux autostart concept and
   references install paths (`/opt/ArcadeAgent/arcade-agent`, XDG autostart, Wayland
   caveats). The new files extend that with concrete, copy-pasteable artifacts.

## Scope (decided)

Produce three artifacts:

### A. `docs/autostart/arcade-agent.desktop` — XDG autostart reference

A canonical example that **mirrors exactly** what `linux.ts` writes at runtime (so
docs and behavior never drift). Header comments document the real `Exec` paths per
install method:

```ini
# Arcade Agent — XDG autostart entry (reference template)
#
# The agent writes its own copy of this file at runtime when auto-start is
# enabled from the Dashboard (Settings -> Agent -> Auto-Start). This file is the
# canonical example to read or to pre-seed manually.
#
# Set Exec to the absolute path of the installed agent binary:
#   .deb install : /opt/Arcade Agent/arcade-agent   (or /usr/bin/arcade-agent)
#   AppImage     : /path/to/Arcade-Agent-*.AppImage
[Desktop Entry]
Type=Application
Name=Arcade Agent
Exec=/opt/arcade-agent/arcade-agent
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
```

### B. `docs/autostart/arcade-agent.service` — systemd unit (two variants)

One documented file presenting **both** install variants, with an explicit
"do not enable both" guard:

- **Primary: user service** — `WantedBy=graphical-session.target`. Runs inside the
  user's graphical login, so `DISPLAY`/`WAYLAND_DISPLAY` exist. Managed with
  `systemctl --user enable --now arcade-agent.service`. Gets journald logging and
  `Restart=on-failure`.
- **Secondary: system service** — `WantedBy=graphical.target`, requires a manually
  injected `Environment=DISPLAY=:0` and an auto-login session. Brittle for a GUI app;
  only for boot-level management with auto-login.

```ini
# Arcade Agent — systemd unit (reference)
#
# The agent is a GUI Electron kiosk and needs a display session.
# Choose ONE mechanism below — do NOT enable both, or the kiosk launches twice.
#
# --- Primary: systemd USER service (recommended) ---
# Install: ~/.config/systemd/user/arcade-agent.service
# Enable : systemctl --user enable --now arcade-agent.service
# Runs in the user's graphical login, so DISPLAY/WAYLAND_DISPLAY are present.
#
# [Unit]
# Description=Arcade Agent (user)
# After=graphical-session.target
#
# [Service]
# ExecStart=/opt/arcade-agent/arcade-agent
# Restart=on-failure
#
# [Install]
# WantedBy=graphical-session.target
#
# --- Secondary: systemd SYSTEM service (requires auto-login + DISPLAY) ---
# Install: /etc/systemd/system/arcade-agent.service
# Enable : sudo systemctl enable --now arcade-agent.service
# Has NO session by default; you must inject DISPLAY and use auto-login.
#
# [Unit]
# Description=Arcade Agent (system)
# After=graphical.target
#
# [Service]
# Environment=DISPLAY=:0
# ExecStart=/opt/arcade-agent/arcade-agent
# Restart=on-failure
#
# [Install]
# WantedBy=graphical.target
#
# Set ExecStart to the installed binary:
#   .deb : /opt/Arcade Agent/arcade-agent  (or /usr/bin/arcade-agent)
#   AppImage: /path/to/Arcade-Agent-*.AppImage
```

### C. `.github/workflows/build-agent-linux.yml` — Linux build verification

Mirrors `build-agent-mac.yml`. This is the only way to actually verify the Linux
build from this repo.

```yaml
name: Build Agent (Linux)

on:
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - 'agent/**'
      - '.github/workflows/build-agent-linux.yml'

jobs:
  build-linux:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: agent
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: "agent/package-lock.json"
      - run: npm ci
      - run: npm run build -- --linux
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: arcade-agent-linux
          path: |
            agent/dist/*.AppImage
            agent/dist/*.deb
          if-no-files-found: error
```

## Non-goals

- **No change to `electron-builder.yml`** — the Linux block already matches the spec.
- **No change to `linux.ts`** — its `enableAutoStart()`/`disableAutoStart()` already
  write/delete the runtime `.desktop`; existing tests cover them.
- **No Windows/macOS autostart doc changes** — those sections already exist in
  `docs/agent-setup.md`.
- **No AppImage/`.deb` code-signing** — unsigned distribution, consistent with the
  macOS approach in `docs/agent-setup.md`.
- **No cross-compile from Windows** — explicitly out of scope; verification is on the
  Linux CI runner.

## Error handling / edge cases

- **Double-launch guard:** the `.service` doc explicitly warns not to enable both the
  user service and the system service (or the XDG `.desktop` and a service) — that
  would start two kiosk instances.
- **Wrong `Exec` path:** both files use the placeholder `/opt/arcade-agent/arcade-agent`
  with commented real paths, so operators substitute the correct one for their
  install method. The doc files are validated by `desktop-file-validate` /
  `systemd-analyze verify` (noted for operators, not run in CI).
- **Wayland:** the existing `linux.ts` warning + `docs/agent-setup.md` Wayland note
  already cover the non-bypass-proof case; the autostart files are display-agnostic
  and need no Wayland-specific handling.

## Verification

1. **CI build:** `build-agent-linux.yml` runs `npm run build -- --linux` on
   `ubuntu-latest` and uploads the `.AppImage` + `.deb`. Green = the Linux build is
   verified. (Cannot be run on the Windows dev host.)
2. **Artifacts:** confirm `dist/*.AppImage` and `dist/*.deb` are produced and uploaded.
3. **Doc syntax:** `.desktop` passes `desktop-file-validate`; `.service` passes
   `systemd-analyze verify` (operator-side, per doc note).
4. **No regression:** existing `tests/platform/*` (including the `linux.ts`
   `enableAutoStart` `.desktop` write test) continue to pass.

## Deliverables checklist

- [ ] `docs/autostart/arcade-agent.desktop` created (reference template)
- [ ] `docs/autostart/arcade-agent.service` created (user + system variants)
- [ ] `.github/workflows/build-agent-linux.yml` created
- [ ] Linux build verified green on `ubuntu-latest` (AppImage + `.deb` uploaded)
- [ ] `docs/TODO.md` Epic 7.2 task items marked complete
