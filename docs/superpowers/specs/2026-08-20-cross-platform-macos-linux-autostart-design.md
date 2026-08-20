# Cross-Platform Deferred Items: macOS, Linux Wayland, Auto-Start

**Date:** 2026-08-20
**Status:** Approved for implementation
**Related:** Section M of `docs/TODO.md` (M.1–M.6)

---

## Overview

This design addresses the six cross-platform deferred items from `docs/release/v1.0-acceptance-results.md`. All items require real-hardware verification; this spec implements code fixes and CI-verifiable tests, with hardware verification checklists for later execution.

**Groups:**
1. **macOS (M.1–M.4)** — Platform service fixes, kiosk overlay, remote commands, launcher build
2. **Linux Wayland (M.5)** — Kiosk verification, compositor quirks, X11 fallback
3. **Auto-Start (M.6)** — systemd, LaunchAgent, Windows startup; boot-time reconnection

---

## Group 1: macOS (M.1–M.4)

### M.1 Restore macOS Platform Service

**File:** `agent/src/main/platform/macos.ts` (already exists, needs fixes)

#### Changes

**1. Fix `BLOCKED_SHORTCUTS` for macOS**
```typescript
// Current (Windows shortcuts):
const BLOCKED_SHORTCUTS = [
  'Alt+F4', 'Alt+Shift+I', 'Control+Shift+I', 'Control+P', 'F12', 'F11', 'Escape',
];

// New (macOS shortcuts):
const BLOCKED_SHORTCUTS = [
  'Meta+Q',           // Cmd+Q — quit app
  'Meta+W',           // Cmd+W — close window
  'Meta+H',           // Cmd+H — hide app
  'Meta+M',           // Cmd+M — minimize
  'Meta+Shift+I',     // Cmd+Shift+I — devtools
  'Control+Shift+I',  // Ctrl+Shift+I — devtools (fallback)
  'Control+P',        // Ctrl+P / Cmd+P — print
  'F12',              // DevTools
  'F11',              // Fullscreen toggle
  'Escape',           // Exit fullscreen
];
```

**2. Use `osascript` for restart/shutdown**
```typescript
async restartPC(): Promise<void> {
  if (isTestMode()) return;
  // osascript triggers graceful restart via System Events (no sudo needed)
  await execAsync("osascript -e 'tell app \"System Events\" to restart'");
}

async shutdownPC(): Promise<void> {
  if (isTestMode()) return;
  // osascript triggers graceful shutdown (requires user session)
  await execAsync("osascript -e 'tell app \"System Events\" to shut down'");
  // Fallback for headless: await execAsync('sudo shutdown -h now');
}
```

**3. Add `agent/tests/platform/macos.test.ts`**
- Mirror structure of `windows.test.ts` / `linux.test.ts`
- Mock: Electron, `child_process`, `sharp`, `systeminformation`, `node:fs/promises`
- Test all 15 `IPlatformService` methods
- Test hotspot polling (full/minimal modes)
- Test power monitor handlers (suspend/resume/lock-screen/unlock-screen)
- Verify `osascript` commands called correctly

### M.2 macOS Kiosk Overlay Verified (AC-13/17)

**Hardware verification checklist:** `docs/checklists/AC-13_macos_kiosk_checklist.md`

| Test | Expected | Known Limitation |
|------|----------|------------------|
| Overlay displays full-screen | ✅ | — |
| Cmd+Q blocked | ✅ (fixed in M.1) | — |
| Cmd+W blocked | ✅ (fixed in M.1) | — |
| Cmd+H blocked | ✅ (fixed in M.1) | — |
| Cmd+M blocked | ✅ (fixed in M.1) | — |
| Cmd+Tab | ❌ | OS-protected — document |
| Cmd+Space (Spotlight) | ❌ | OS-protected — document |
| Cmd+Opt+Esc (Force Quit) | ❌ | OS-protected — document |
| Ctrl+Cmd+Power | ❌ | OS-protected — document |
| Screen Recording permission | ✅ grant in Settings | Required for screenshots |
| Accessibility permission | ✅ grant in Settings | Required for shortcut blocking |

**Documentation updates:** `docs/agent-setup.md` → "macOS Known Limitations" table

### M.3 macOS Remote Commands Verified (AC-14)

**Hardware verification checklist:** `docs/checklists/AC-14_macos_remote_commands_checklist.md`

| Command | Method | Verification |
|---------|--------|--------------|
| Restart | `osascript -e 'tell app "System Events" to restart'` | Agent restarts, reconnects |
| Shutdown | `osascript -e 'tell app "System Events" to shut down'` | Machine powers off |
| Screenshot | `desktopCapturer` + `sharp` | Returns JPEG ≤1280×720, q80 |

**Documentation:** Add `sudoers` note for fallback `sudo shutdown`:
```bash
# /etc/sudoers.d/arcade-agent
arcade-agent ALL=(ALL) NOPASSWD: /sbin/shutdown
```

### M.4 macOS Launcher Verified (AC-15)

**Verification steps (CI + hardware):**
1. `brew install python-tk` (Tcl/Tk headers for PyInstaller)
2. `python build.py --only launcher` → produces `dist/Arcade Launcher.app/`
3. Run `./dist/Arcade Launcher.app/Contents/MacOS/Arcade Launcher --self-test`
4. Verify Tkinter UI renders, uvicorn subprocess starts on "Start Server"

**Build script:** No changes needed — `arcade.spec` and `build.py` are cross-platform.

---

## Group 2: Linux Wayland (M.5)

### M.5 Linux Wayland Kiosk Verified (AC-13)

#### Current Behavior
```typescript
// In linux.ts showKioskOverlay():
if (isWayland()) {
  win.setKiosk(true);
  win.maximize();
  win.setAlwaysOnTop(true, 'screen-saver');
  console.warn('[linux] Wayland detected: kiosk overlay is NOT bypass-proof...');
}
```

#### CI Smoke Tests (add to `agent/tests/platform/linux.test.ts`)
```typescript
// Wayland detection
it('isWayland true under XDG_SESSION_TYPE=wayland', () => { ... });
it('isWayland true when WAYLAND_DISPLAY is set', () => { ... });

// Wayland kiosk flags applied
it('applies Wayland kiosk flags when isWayland()', () => {
  process.env.XDG_SESSION_TYPE = 'wayland';
  service.showKioskOverlay({...});
  expect(mockWin.setKiosk).toHaveBeenCalledWith(true);
  expect(mockWin.maximize).toHaveBeenCalled();
  expect(mockWin.setAlwaysOnTop).toHaveBeenCalledWith(true, 'screen-saver');
});

// Screenshot fallback on Wayland
it('throws clear error when no screen sources (Wayland)', async () => {
  vi.mocked(desktopCapturer.getSources).mockResolvedValueOnce([]);
  await expect(service.captureScreenshot()).rejects.toThrow(/Screenshot unavailable/);
});
```

#### Documentation Updates (`docs/agent-setup.md`)
- **GNOME Wayland:** Compositor owns window stacking; `setAlwaysOnTop('screen-saver')` non-functional (`electron#50403`)
- **KDE Wayland:** Similar limitations; KWin may allow some kiosk hints
- **X11 Fallback (recommended for v1.0):**
  ```bash
  # Cage (lightweight)
  cage /opt/arcade-agent/arcade-agent --ozone-platform-hint=auto

  # gnome-kiosk (GNOME)
  gnome-kiosk /opt/arcade-agent/arcade-agent

  # ubuntu-frame (Ubuntu Core)
  ubuntu-frame /opt/arcade-agent/arcade-agent
  ```
- **Screenshots:** Require PipeWire portal + user grant; fail with clear error if denied

#### Hardware Verification Checklist
`docs/checklists/AC-13_linux_wayland_kiosk_checklist.md` — test matrix:
- GNOME Wayland (Ubuntu 24.04, Fedora 40)
- KDE Wayland (Kubuntu 24.04, Fedora KDE 40)
- X11 + Cage / gnome-kiosk / ubuntu-frame

---

## Group 3: Auto-Start All OSes (M.6)

### M.6 Agent Auto-Start on All OSes

#### Production-Ready Unit Files

**Linux — systemd user service** (`docs/autostart/arcade-agent.service`)
```ini
[Unit]
Description=Arcade Agent
After=graphical-session.target

[Service]
Type=simple
ExecStart=/opt/arcade-agent/arcade-agent
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
# For Wayland: Environment=WAYLAND_DISPLAY=wayland-0

[Install]
WantedBy=graphical-session.target
```
**Install:** `systemctl --user enable --now arcade-agent.service`

**macOS — LaunchAgent plist** (`docs/autostart/com.arcade.agent.plist`)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.arcade.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/Arcade Agent.app/Contents/MacOS/Arcade Agent</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/arcade-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/arcade-agent.err.log</string>
</dict>
</plist>
```
**Install:** `launchctl load ~/Library/LaunchAgents/com.arcade.agent.plist`

**Windows — Registry (existing) + documented**
- Current: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` → `ArcadeAgent`
- For pre-login service: document NSSM wrapper as v2 enhancement

#### Integration Tests

**File:** `agent/tests/platform/autostart.test.ts`
```typescript
// Linux: verify .desktop file written to ~/.config/autostart/
// macOS: verify .plist written to ~/Library/LaunchAgents/
// Windows: verify registry value written to HKCU\...\Run
// All: verify correct Exec/ProgramArguments path, permissions
```

**Frontend test:** `frontend/src/components/AutoStartToggle.test.tsx`
- Toggle Settings → Agent → Auto-Start
- Verify `SET_AUTO_START` command sent via WebSocket
- Verify platform `enableAutoStart()` / `disableAutoStart()` called

#### Boot-Time Reconnection Logic
- Agent reads `agent.config.json` on start
- Connects to WebSocket server with `seat_id` + `agent_secret`
- Server validates, sends `INIT` payload with config
- Agent shows kiosk overlay (`AVAILABLE` state)
- **Config:** `reconnect_max_seconds: 60` (default), `health_interval_seconds: 60`

#### Documentation Updates (`docs/agent-setup.md`)
- Replace reference templates with production files above
- Add installation commands per OS
- Add troubleshooting:
  - "Agent starts but doesn't connect" → check logs, config path, network
  - "Auto-start enabled but agent not running" → check `journalctl --user -u arcade-agent` / `launchctl list` / Task Manager

---

## Testing Strategy

| Layer | macOS | Linux Wayland | Auto-Start |
|-------|-------|---------------|------------|
| **Unit** | `macos.test.ts` (new) | Extended `linux.test.ts` | `autostart.test.ts` (new) |
| **Integration** | Dashboard → agent `SET_AUTO_START` | Dashboard → agent `SET_AUTO_START` | Frontend toggle test |
| **CI** | All unit tests on Windows (mocked) | All unit tests on Windows (mocked) | All unit tests on Windows |
| **Hardware** | Checklists M.2–M.4 | Checklist M.5 | Checklist M.6 |

---

## Files to Create/Modify

### New Files
- `agent/tests/platform/macos.test.ts`
- `agent/tests/platform/autostart.test.ts`
- `docs/checklists/AC-13_macos_kiosk_checklist.md`
- `docs/checklists/AC-14_macos_remote_commands_checklist.md`
- `docs/checklists/AC-15_macos_launcher_checklist.md`
- `docs/checklists/AC-13_linux_wayland_kiosk_checklist.md`
- `docs/autostart/com.arcade.agent.plist` (production version)
- `docs/autostart/arcade-agent.service` (production version)

### Modified Files
- `agent/src/main/platform/macos.ts` — shortcuts, osascript commands
- `agent/tests/platform/linux.test.ts` — Wayland smoke tests
- `docs/agent-setup.md` — limitations, auto-start files, Wayland docs
- `frontend/src/components/AutoStartToggle.test.tsx` (new or extend existing)

---

## Acceptance Criteria

| Item | CI Verified | Hardware Verified |
|------|-------------|-------------------|
| M.1 macOS platform service | ✅ unit tests pass | ✅ checklist |
| M.2 macOS kiosk overlay | ✅ shortcut blocking tests | ✅ checklist |
| M.3 macOS remote commands | ✅ osascript calls tested | ✅ checklist |
| M.4 macOS launcher | ⚠️ build script runs | ✅ checklist |
| M.5 Linux Wayland | ✅ detection/flags tests | ✅ checklist |
| M.6 Auto-start | ✅ unit + integration tests | ✅ checklist |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| macOS shortcuts differ by keyboard layout | Test with US layout; document as known |
| `osascript` requires user session (not headless) | Document fallback `sudo shutdown` + sudoers |
| Wayland compositor quirks vary | Document X11 fallback as recommended path |
| Auto-start fails on boot (network not ready) | Agent reconnect logic handles this (60s max) |
| Unsigned macOS app loses permissions on rebuild | Document Gatekeeper bypass; notarization v2 |

---

## Rollout Plan

1. **Phase 1 (Code):** Implement macOS.ts fixes, add macos.test.ts, linux.test.ts Wayland tests, autostart.test.ts
2. **Phase 2 (Docs):** Update agent-setup.md, create checklists, add production unit files
3. **Phase 3 (CI):** All tests pass on Windows CI
4. **Phase 4 (Hardware):** Execute checklists on physical Mac / Linux Wayland / Windows
5. **Phase 5 (Close):** Update `docs/TODO.md` M.1–M.6 to `[x]`, update `v1.0-acceptance-results.md`

---

## Self-Review Checklist

- [x] No TBD/TODO placeholders
- [x] All 6 items addressed with specific code changes
- [x] CI-verifiable tests defined for each
- [x] Hardware verification checklists specified
- [x] Documentation updates identified
- [x] No scope creep — focused on Section M only
- [x] Existing patterns followed (mirrors windows.test.ts/linux.test.ts)
