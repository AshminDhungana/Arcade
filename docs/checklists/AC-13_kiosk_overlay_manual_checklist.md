# AC-13: Kiosk Overlay — Manual Verification Checklist

## Overview
The agent uses a full-screen Electron `BrowserWindow` with `kiosk: true`, `closable: false`, `devTools: false` as the access control mechanism. This overlay blocks OS-level input on Windows/macOS/Linux. No OS lock/unlock APIs are used.

## Test Environment Requirements
- **Windows 10/11** (test on physical machine or VM)
- **macOS 12+** (test on physical Mac or CI Mac runner)
- **Linux (Ubuntu 22.04+, Fedora 38+)** - test on both X11 and Wayland

## Manual Test Steps

### 1. Kiosk Overlay Activation
- [ ] Start agent on client PC
- [ ] Verify agent connects to server (websocket connected)
- [ ] Start session from dashboard (walk-in or member)
- [ ] **Verify**: Kiosk overlay appears immediately, covering entire screen
- [ ] **Verify**: No window decorations, taskbar, dock, or system UI visible
- [ ] **Verify**: `kiosk: true`, `closable: false`, `devTools: false` in Electron window options

### 2. Windows-Specific (Win32)
- [ ] **Alt+F4**: Press Alt+F4 — overlay should NOT close (intercepted)
- [ ] **Ctrl+Alt+Del**: Press Ctrl+Alt+Del — **KNOWN LIMITATION**: OS security screen appears (cannot intercept)
- [ ] **WinKey**: Press Windows key — Start menu should NOT appear (or overlay stays on top)
- [ ] **Ctrl+Shift+Esc**: Task Manager should NOT appear (or overlay stays on top)
- [ ] **Win+L**: Lock screen — **KNOWN LIMITATION**: OS locks (cannot intercept)

### 3. macOS-Specific
- [ ] **Cmd+Q**: Press Cmd+Q — overlay should NOT close (intercepted via `before-quit` / `window-all-closed` prevention)
- [ ] **Cmd+Option+Esc**: Force Quit menu — overlay should stay on top
- [ ] **Ctrl+Cmd+F**: Fullscreen toggle — should not affect kiosk window
- [ ] **Mission Control / Exposé**: Should not escape overlay

### 4. Linux-Specific
- [ ] **X11**: Alt+F4, Super key — intercepted by Electron kiosk mode
- [ ] **Wayland**: Known compositor variations — test on GNOME (Wayland) and KDE (Wayland)
- [ ] **Ctrl+Alt+F1-F7**: TTY switching — **KNOWN LIMITATION**: Cannot intercept
- [ ] **Compositor crashes**: Verify overlay restarts with agent process

### 5. Cross-Platform Session Flow
- [ ] Start session → kiosk shows → session runs 30+ seconds
- [ ] Pause session from dashboard → kiosk shows "Paused" overlay
- [ ] Resume session → kiosk shows timer continuing
- [ ] End session from dashboard → kiosk hides, seat returns to AVAILABLE
- [ ] Agent crashes mid-session → on restart, kiosk restores from local cache (SYNC reconciliation)

### 6. Multi-Monitor
- [ ] Verify kiosk spans primary monitor (or all monitors if configured)
- [ ] Verify secondary monitor content is blocked/black on Windows/macOS

### 7. Power Events
- [ ] Sleep/wake cycle — kiosk restores on wake
- [ ] Laptop lid close/open — kiosk restores

## Known Limitations (Documented, Not Bugs)
| Limitation | Platform | Mitigation |
|---|---|---|
| Ctrl+Alt+Del | Windows | Physical security at venue; staff monitoring |
| Win+L | Windows | Physical security; staff monitoring |
| Cmd+Option+Esc | macOS | Kiosk stays on top; Force Quit kills agent process |
| Ctrl+Alt+F1-F7 | Linux (X11/Wayland) | Physical security; disable TTY switching in kiosk kiosk mode |
| Wayland compositor quirks | Linux (Wayland) | Test on target distro; use X11 fallback if needed |

## Pass/Fail Criteria
- **PASS**: All ✅ checks pass on target platform
- **FAIL**: Any ✅ check fails on target platform
- **KNOWN LIMITATION**: Documented gaps above are acceptable for v1.0

## Evidence
- Record short video (30-60s) of each platform test
- Screenshot of kiosk overlay active
- Screenshot of dashboard seat status = IN_USE while kiosk shown
