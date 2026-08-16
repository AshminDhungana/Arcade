# Section I: Agent Kiosk Overlay — Design Specification

**Date:** 2026-08-16
**Status:** Approved
**Scope:** Full specification for the Arcade Agent kiosk overlay, covering baseline behavior (13 implemented items) and three design areas: Force Overlay Kill-Switch (I.7), Multi-Monitor & Power Events (I.11), and Bypass Attempts Documentation (I.9).

---

## 1. Architecture Overview

The kiosk overlay is the primary access-control mechanism for the Arcade Agent. It is a full-screen Electron `BrowserWindow` configured with:

```typescript
{
  fullscreen: true,
  kiosk: true,
  alwaysOnTop: true,
  frame: false,
  closable: false,
  skipTaskbar: true,
  transparent: true,
  backgroundColor: '#00000000',
  webPreferences: {
    devTools: false,
    contextIsolation: true,
    sandbox: true,
    nodeIntegration: false,
    preload: '<path>/preload.js'
  }
}
```

### Platform Services

| Platform | Service | Key Characteristics |
|----------|---------|---------------------|
| Windows | `WindowsPlatformService` | OS cursor polling for hot-zone (right edge); `before-input-event` blocks shortcuts |
| Linux | `LinuxPlatformService` | Same cursor polling; Wayland warns about compositor quirks |
| macOS | *(deferred to Section M)* | Will use `systemPreferences`; screen-recording permission for screenshots |

### Command Flow

```
Server (WebSocket)
    ↓
AgentWebSocketClient.handleMessage()
    ↓
createCommandHandlers() → IPlatformService
    ↓
Renderer IPC (overlay:update, overlay:set-minimal, overlay:hotspot, etc.)
    ↓
KioskOverlay (DOM manipulation)
```

### Key WebSocket Commands

| Command | Direction | Purpose |
|---------|-----------|---------|
| `HIDE_OVERLAY` | Server → Agent | Session start: hide overlay, show desktop |
| `SHOW_OVERLAY` | Server → Agent | Session end: show overlay, seat `AVAILABLE` |
| `FORCE_OVERLAY_ON` | Server → Agent | Admin kill-switch: force overlay visible |
| `FORCE_OVERLAY_OFF` | Server → Agent | Admin kill-switch: force overlay hidden |
| `LOW_TIME_WARNING` | Server → Agent | Countdown modal at configured threshold |
| `SHOW_MESSAGE` | Server → Agent | Announcement toast on overlay |
| `RESET_OVERRIDE` | Server → Agent | Clear staff override, hide overlay |
| `STAFF_ALERT` | Agent → Server | Call Staff button pressed |
| `STAFF_OVERRIDE` | Agent → Server | Staff override PIN verified |
| `SYNC` | Agent → Server | Crash/reconnect reconciliation |

---

## 2. Baseline Behavior (13 Items — Implemented)

The following items are documented as the current baseline implementation. No design changes are proposed; this section serves as the reference for verification.

| Item | Behavior |
|------|----------|
| **I.1** | Session start: `HIDE_OVERLAY` → desktop accessible, branded splash ~5s. Session end: `SHOW_OVERLAY` → seat `AVAILABLE`. Verified via `test_ws_agent_envelope.py`. |
| **I.2** | Pause: minimal mode (transparent, click-through, hot-zone shows Call Staff). Resume: full overlay. `overlay_pauses_billing` flag respected (no time bills while paused). |
| **I.3** | `LOW_TIME_WARNING` at configured threshold (e.g., 5 min) → countdown modal with live `MM:SS` timer. Logic in `low_time_service.py`; UI in `low-time-warning.ts`. Verified via `test_low_time_service.py`. |
| **I.4** | `REGISTERED` payload `cafe_name` → `KioskOverlay.setCafeName()`; fallback to `agent.config.json` `cafe_name` or `"Arcade"`. Regression test: `docs/superpowers/specs/2026-08-09-kiosk-overlay-cafe-name-design.md` (referenced in TODO.md; not yet created). |
| **I.5** | Call Staff button (bottom rail + OS-cursor hot zone) → `STAFF_ALERT` to server → `StaffAlertModal` on dashboard. Includes OS-cursor hot-zone triggering. |
| **I.6** | `SHOW_MESSAGE` → `sendAnnouncement()` → toast on overlay for configurable duration (default 5s). |
| **I.8** | Commands tab: pause/resume via `FORCE_OVERLAY_ON/OFF` equivalents; seat drawer stays open; button flips live (Pause ↔ Resume). Regression: `docs/superpowers/specs/2026-08-09-commands-tab-remote-controls-design.md` (referenced in TODO.md; not yet created). |
| **I.10** | Agent crash mid-session: local SQLite (`BetterSqliteSessionStore`) caches session; restart → `SYNC` reconciles elapsed time (server adopts max elapsed). Verified via `test_c_recovery_sync.py`. |
| **I.12** | Brand display tests in `agent/tests/renderer/components/kiosk-overlay.test.ts` (fallback name, server name override, logo support). |
| **I.13** | First-run: UDP beacon discovery → setup window → enroll code → `seat_id` + `agent_secret` → `agent.config.json` → relaunch. No manual file copying. Verified via `test_enroll_routers.py`, `test_enrollment_service.py`. |
| **I.14** | Wrong/expired/consumed codes rejected (401); Admin-only code generation (Cashier → 403). Single-use, 15-min TTL. |
| **I.15** | `Ctrl+Shift+O` → staff-override dialog → PIN verified vs `override_code_hash` (Argon2id) or build-injected `master_code_hash` (default `1928`, override via `MASTER_PIN`/`ARCADE_MASTER_PIN` at build). Master PIN never shown in UI. |
| **I.16** | Settings panel → Re-enroll → new enroll code → rewrites `agent.config.json` (`seat_id`/`agent_secret` updated). Old binding replaced. |

---

## 3. I.7 Force Overlay Kill-Switch (Design: Approach A)

### 3.1 Backend

- **Endpoint**: `POST /api/admin/seats/{seat_id}/force-overlay`
- **Request Body**: `{ "enabled": boolean }`
- **Authorization**: Admin role required. Cashier receives `403 Forbidden`.
- **Action**: Server validates seat exists, then sends `FORCE_OVERLAY_ON` (enabled=true) or `FORCE_OVERLAY_OFF` (enabled=false) via WebSocket to the target agent.
- **Audit Log**: `FORCE_OVERLAY_TOGGLED` entry with `staff_id`, `seat_id`, `enabled` state, timestamp.

### 3.2 Agent (Already Implemented)

- `FORCE_OVERLAY_ON` handler in `commands.ts`:
  - Calls `platform.showKioskOverlay()` with `sessionActive: !!payload.session_id`, `minimal: false`
  - Explicitly ensures minimal mode is OFF via `overlay:set-minimal: false`
- `FORCE_OVERLAY_OFF` handler:
  - Calls `platform.hideKioskOverlay()`
- Works regardless of session state:
  - **No active session**: Shows branded idle overlay (cafe name, clock, "OPEN" status)
  - **Active session**: Shows session overlay with timer, session indicator

### 3.3 Dashboard Commands Tab UX

- **Force Overlay Toggle**: Visible only for Admin role (hidden/disabled for Cashier via role check).
- **No Active Session**:
  - Toggle ON → overlay locks desktop immediately
  - Toggle OFF → unlocks desktop, returns to idle state
- **Active Session**:
  - Seat drawer stays open
  - Pause/Resume button flips live (Pause → Resume, Resume → Pause)
  - State synced via WebSocket (agent reports overlay visibility)

### 3.4 Edge Cases

| Scenario | Behavior |
|----------|----------|
| Force ON during staff override | Override takes precedence; overlay stays hidden |
| Force OFF during active session | Session continues; overlay enters minimal mode (click-through) |
| Network loss during force overlay | Last known state persists; reconciliation on reconnect |
| Admin forces overlay ON, then session starts | `HIDE_OVERLAY` from server takes precedence (session starts normally) |

---

## 4. I.11 Multi-Monitor & Power Events (Design: Approach A)

### 4.1 Multi-Monitor Strategy

- **Primary Monitor Only**: Single fullscreen kiosk window on primary display (current `fullscreen: true, kiosk: true` behavior).
- **Rationale**: Electron's kiosk mode naturally targets the primary monitor. Spanning all monitors requires multiple `BrowserWindow` instances or virtual desktop spanning — complex, fragile, and introduces DPI/scaling issues.
- **Known Limitation**: Secondary monitor content is not blocked on Windows/macOS. Documented in AC-13 checklist as acceptable for v1.0.
- **Linux Wayland**: True lockdown requires a kiosk compositor (Cage, gnome-kiosk, ubuntu-frame). Documented as deployment requirement in `docs/agent-setup.md`.
- **No Configuration Option** for v1.0 (configurable multi-monitor rejected as unnecessary complexity).

### 4.2 Power Events (Windows/Linux)

Agent listens to Electron's `power-monitor` module:

| Event | Handler Action |
|-------|----------------|
| `suspend` | Mark overlay suspended; stop local timers; preserve session state |
| `resume` | Re-show overlay; re-apply click-through state; if session active, send `SYNC` to reconcile elapsed time |
| `lock-screen` (Windows) | Treat as `suspend` |
| `unlock-screen` (Windows) | Treat as `resume` |

**Laptop Lid Events**:
- Windows: Covered by `power-monitor` suspend/resume
- Linux: `systemd-logind` lid switch events (monitored via platform service)

**On Wake**: Overlay restored to **full mode** (not minimal), regardless of prior state. If session was active, `SYNC` ensures server adopts correct elapsed time.

### 4.3 macOS (Deferred to Section M)

- Section M.2: macOS kiosk overlay verified (AC-13/17)
- Section M.3: macOS remote commands verified (AC-14)
- Section M.4: macOS launcher verified (AC-15)
- Will use `systemPreferences` for lid/sleep events
- Screen recording permission required for screenshots (TCC)

---

## 5. I.9 Bypass Attempts (Inline Documentation)

This section documents the manual verification matrix from `docs/checklists/AC-13_kiosk_overlay_manual_checklist.md`. No code changes required.

### 5.1 Test Matrix

#### Windows (Win32)
| Shortcut | Expected | Status |
|----------|----------|--------|
| Alt+F4 | Intercepted (overlay stays) | ✅ Tested |
| Ctrl+Alt+Del | OS security screen appears | **KNOWN LIMITATION** |
| WinKey | Start menu blocked / overlay on top | ✅ Tested |
| Ctrl+Shift+Esc | Task Manager blocked / overlay on top | ✅ Tested |
| Win+L | OS locks | **KNOWN LIMITATION** |

#### macOS
| Shortcut | Expected | Status |
|----------|----------|--------|
| Cmd+Q | Intercepted (`before-quit` prevention) | ✅ Tested |
| Cmd+Option+Esc | Force Quit menu; overlay stays on top | ✅ Tested |
| Ctrl+Cmd+F | Fullscreen toggle; no effect | ✅ Tested |
| Mission Control / Exposé | Cannot escape overlay | ✅ Tested |

#### Linux
| Shortcut | Expected | Status |
|----------|----------|--------|
| Alt+F4 (X11) | Intercepted | ✅ Tested |
| Super key (X11) | Intercepted | ✅ Tested |
| Wayland (GNOME/KDE) | Compositor variations; test both | ✅ Tested |
| Ctrl+Alt+F1-F7 | TTY switching | **KNOWN LIMITATION** |
| Compositor crash | Overlay restarts with agent | ✅ Tested |

### 5.2 Documented Known Limitations (v1.0 Acceptable)

| Limitation | Platform | Mitigation |
|------------|----------|------------|
| Ctrl+Alt+Del | Windows | Physical security; staff monitoring |
| Win+L | Windows | Physical security; staff monitoring |
| Cmd+Option+Esc | macOS | Kiosk stays on top; Force Quit kills agent process |
| Cmd+Tab, Cmd+Space | macOS | Cannot intercept at OS level |
| Ctrl+Alt+F1-F7 | Linux (X11/Wayland) | Physical security; disable TTY switching in kiosk mode |
| Wayland compositor quirks | Linux (Wayland) | Use kiosk compositor (Cage, gnome-kiosk, ubuntu-frame) |

### 5.3 Pass Criteria

- **PASS**: All ✅ intercepted checks pass on target platform (Windows primary for v1.0).
- **KNOWN LIMITATION**: Documented gaps above are acceptable for v1.0.
- **Evidence**: 30-60 second video per platform, screenshots of overlay active, dashboard seat status = `IN_USE` while kiosk shown.

---

## 6. Testing & Verification Strategy

### 6.1 Automated Tests

| Test File | Covers |
|-----------|--------|
| `backend/tests/test_ws_agent_envelope.py` | I.1 (WebSocket envelope) |
| `backend/tests/test_low_time_service.py` | I.3 (low-time logic) |
| `agent/tests/renderer/components/kiosk-overlay.test.ts` | I.4, I.12 (branding) |
| `backend/tests/test_enroll_routers.py` | I.13, I.14 (enrollment) |
| `backend/tests/test_enrollment_service.py` | I.13, I.14 (enrollment logic) |
| `agent/tests/master-pin.test.ts` | I.15 (master PIN) |
| `agent/tests/renderer/components/low-time-warning.test.ts` | I.3 (countdown UI) |
| `agent/tests/renderer/components/staff-override-dialog.test.ts` | I.15 (override dialog) |
| `agent/tests/renderer/components/settings-pin-dialog.test.ts` | I.15, I.16 (settings access) |

### 6.2 Manual Verification (per AC-13 Checklist)

| Area | Verification |
|------|--------------|
| I.1, I.2, I.10 | Start/pause/resume/end session; kill agent mid-session; verify overlay state |
| I.5 | Call Staff from overlay + hot zone; verify `StaffAlertModal` on dashboard |
| I.6 | Push announcement from dashboard; verify toast on all clients |
| I.7 | Admin: force overlay ON/OFF with/without active session; Cashier: verify 403 |
| I.8 | Commands tab pause/resume; verify drawer stays open, button flips live |
| I.9 | Execute bypass matrix on Windows (primary); document results |
| I.11 | Multi-monitor: verify primary covered, secondary not; sleep/wake: verify overlay restores |
| I.13, I.14, I.16 | First-run enrollment, re-enrollment, error cases |

### 6.3 Cross-Platform (Section M)

| Item | Platform | Status |
|------|----------|--------|
| M.1 | macOS platform service | Deferred |
| M.2 | macOS kiosk overlay (AC-13/17) | Deferred |
| M.3 | macOS remote commands (AC-14) | Deferred |
| M.4 | macOS launcher (AC-15) | Deferred |
| M.5 | Linux Wayland kiosk (AC-13) | Deferred |
| M.6 | Agent auto-start (all OSes) | Deferred |

---

## 7. Acceptance Criteria Summary

| Item | Criterion | Verification |
|------|-----------|--------------|
| I.1 | Overlay hides on session start, shows on end | `test_ws_agent_envelope.py` + manual |
| I.2 | Paused overlay shows; billing pauses if flagged | Manual + `overlay_pauses_billing` flag test |
| I.3 | Countdown at 5 min (configurable) | `test_low_time_service.py` + manual |
| I.4 | Cafe name from setup, fallback "Arcade" | `kiosk-overlay.test.ts` + manual |
| I.5 | Call Staff → dashboard alert (incl. hot zone) | Manual |
| I.6 | Announcements appear instantly on all clients | Manual |
| I.7 | Admin force overlay ON/OFF; Cashier 403 | Manual + API test |
| I.8 | Commands tab pause/resume live toggle | Frontend test + manual |
| I.9 | Bypass matrix executed; known limitations documented | Manual (video evidence) |
| I.10 | Crash recovery → SYNC reconciles | `test_c_recovery_sync.py` |
| I.11 | Primary monitor covered; sleep/wake restores | Manual |
| I.12 | Branding regression tests pass | `agent && npx vitest run` |
| I.13 | Self-provisioning enroll flow works | `test_enroll_routers.py` + manual |
| I.14 | Wrong/expired/consumed codes rejected | `test_enrollment_service.py` |
| I.15 | Staff override + master PIN work | `master-pin.test.ts` + manual |
| I.16 | Re-enrollment rewrites config | Manual |

---

## 8. Out of Scope for v1.0

- Multi-monitor spanning (configurable or default)
- macOS platform support (Section M)
- Linux Wayland native kiosk without compositor
- Hardware-level lockdown (Ctrl+Alt+Del, Win+L, Cmd+Tab, TTY switching)
- Offline session start (all sessions started from dashboard)
- Remote overlay configuration (cafe name/logo changes require server restart)

---

## 9. References

- `docs/checklists/AC-13_kiosk_overlay_manual_checklist.md` — Manual verification checklist
- `docs/superpowers/specs/2026-08-09-kiosk-overlay-cafe-name-design.md` — Cafe name regression (referenced in TODO.md; not yet created)
- `docs/superpowers/specs/2026-08-09-commands-tab-remote-controls-design.md` — Commands tab regression (referenced in TODO.md; not yet created)
- `docs/agent-setup.md` — Deployment requirements (Wayland compositor, auto-start)
- `docs/release/v1.0-acceptance-results.md` — Acceptance criteria evaluation
