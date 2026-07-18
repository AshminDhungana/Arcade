# Agent Kiosk Hardening Verification Matrix

> Cross-platform verification of the Arcade Agent's kiosk shortcut hardening.
> Part of Epic 7.3. Design spec: `./specs/2026-07-18-kiosk-hardening-verification-design.md`.

## How to use

1. Capture the test environment (template below) for each run.
2. For each row, perform the **Verification step** on real hardware running the café's target OS.
3. Fill the **Result** cell: `PASS` (matches Expected), `FAIL` (does not), or `N/A` (not executable yet — see macOS gate).
4. Log the run in the footer.

## Disposition legend

- **BLOCKED (app)** — Arcade's own code prevents it (a `before-input-event` trap, `devTools:false`, or a `globalShortcut` no-op). Verify it stays blocked.
- **BLOCKED (kiosk)** — Electron's `kiosk:true` / OS presentation flag prevents it. Verify.
- **GAP** — No app or flag can prevent it at the user level. Documented; remediation noted where one exists.

## Environment capture template

```
Run date:
Engineer:
Arcade version:
Electron version:
OS (build):            e.g. Windows 11 22H2 / macOS 15.4 / Ubuntu 24.04
DE / WM (Linux):       e.g. GNOME-X11 / KDE / XFCE / Sway (Wayland)
Session type (Linux):  X11 | Wayland
```

## Windows

Code baseline: `agent/src/main/platform/windows.ts` — `before-input-event` blocks `Alt+F4, Alt+Shift+I, Control+Shift+I, Control+P, F12, F11, Escape`; every `BrowserWindow` sets `devTools:false`.

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| W1 | Alt+F4 | Close window | BLOCKED (app) | `before-input-event` + `closable:false` (`windows.ts:44-58,65-79`) | Kiosk overlay does not close; no exit. | With overlay shown, press Alt+F4. | Win 11 (build) | | |
| W2 | F12 | DevTools | BLOCKED (app) | `before-input-event` + `devTools:false` (`windows.ts:51,76`) | No DevTools window opens. | Press F12. | Win 11 | | |
| W3 | Ctrl+Shift+I | DevTools | BLOCKED (app) | `before-input-event` (`windows.ts:21,76`) | No DevTools. | Press Ctrl+Shift+I. | Win 11 | | |
| W4 | Alt+Shift+I | DevTools (Edge-style) | BLOCKED (app) | `before-input-event` (`windows.ts:20,76`) | No DevTools / feedback pane. | Press Alt+Shift+I. | Win 11 | | |
| W5 | Ctrl+P | Print | BLOCKED (app) | `before-input-event` (`windows.ts:23,76`) | No print dialog. | Press Ctrl+P. | Win 11 | | |
| W6 | F11 | Fullscreen toggle | BLOCKED (app) | `before-input-event` (`windows.ts:24,76`) | No fullscreen exit. *Observation: defensive, not in todo.* | Press F11. | Win 11 | | |
| W7 | Escape | Esc | BLOCKED (app) | `before-input-event` (`windows.ts:25,76`) | No overlay dismiss. *Observation: defensive, not in todo.* | Press Escape. | Win 11 | | |
| W8 | Ctrl+Shift+Esc | Task Manager | GAP | — | Cannot block at app level (OS-level). | Press Ctrl+Shift+Esc. | Win 11 | | Documented limitation. |
| W9 | Ctrl+Alt+Del | Secure Attention Sequence | GAP | — | Cannot block (by design). | Press Ctrl+Alt+Del. | Win 11 | | Permanent limitation. |
| W10 | Win+D | Show desktop / taskbar | GAP | — | Exposes taskbar (`electron#38020`, unresolved). | Press Win+D. | Win 11 | | Remediation: shell replacement (`Winlogon\Shell`). |
| W11 | Win+L | Lock | GAP | — | Locks session. | Press Win+L, then unlock. | Win 11 | | Document re-show-on-unlock. |
| W12 | Sticky Keys (Shift×5) | Accessibility | GAP | — | Opens Sticky Keys prompt (pivot to settings). | Press Shift 5×. | Win 11 | | Remediation: disable via Group Policy. |
| W13 | PrintScreen / Win+Shift+S | Screen capture | GAP | — | OS capture unaffected. | Press PrintScreen. | Win 11 | | OS-level. |

## macOS

> **Execution gate:** Authored against Epic 7.1 design §3 (`./specs/2026-07-18-macos-platform-design.md`). `macos.ts` is not yet implemented — **execute these rows when Epic 7.1 lands.** Until then mark Result `N/A`.

Mitigations (per 7.1 design): null application menu + `globalShortcut` no-ops + `before-input-event` + `kiosk:true` presentation flag.

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| M1 | Cmd+Q | Quit | BLOCKED (app) | `globalShortcut` no-op (`macos.ts` §3) | App does not quit. | Press Cmd+Q. | macOS (ver) | N/A | Gate: 7.1 |
| M2 | Cmd+W | Close window | BLOCKED (app) | `globalShortcut` no-op + null menu | No close. | Press Cmd+W. | macOS | N/A | Gate: 7.1 |
| M3 | Cmd+H | Hide | BLOCKED (app) | `globalShortcut` no-op + null menu | No hide. | Press Cmd+H. | macOS | N/A | Gate: 7.1 |
| M4 | Cmd+M | Minimize | BLOCKED (app) | `globalShortcut` no-op + null menu | No minimize. | Press Cmd+M. | macOS | N/A | Gate: 7.1 |
| M5 | F12 | DevTools | BLOCKED (app) | `globalShortcut` + input trap | No DevTools. | Press F12. | macOS | N/A | Gate: 7.1 |
| M6 | Cmd+Shift+I | DevTools | BLOCKED (app) | `globalShortcut` + input trap | No DevTools. | Press Cmd+Shift+I. | macOS | N/A | Gate: 7.1 |
| M7 | Alt+Shift+I | DevTools | BLOCKED (app) | `globalShortcut` + input trap | No DevTools. | Press Alt+Shift+I. | macOS | N/A | Gate: 7.1 |
| M8 | Cmd+P | Print | BLOCKED (app) | `globalShortcut` + input trap | No print dialog. | Press Cmd+P. | macOS | N/A | Gate: 7.1 |
| M9 | Cmd+Tab | App switch | BLOCKED (kiosk) | `kiosk:true` → `NSApplicationPresentationOptions` | Cannot switch apps. | Press Cmd+Tab. | macOS | N/A | Gate: 7.1 |
| M10 | Cmd+Space | Spotlight | BLOCKED (kiosk) | kiosk presentation flag | No Spotlight. | Press Cmd+Space. | macOS | N/A | Gate: 7.1 |
| M11 | Menu bar / Dock | OS chrome | BLOCKED (kiosk) | `kiosk:true` | Hidden. | Observe during session. | macOS | N/A | Gate: 7.1 |
| M12 | Cmd+Opt+Space | Finder search | GAP | — | Bypass even when Cmd+Space blocked. | Press Cmd+Opt+Space. | macOS | N/A | Blur re-assertion suggested (`./references/ARCH-02-kiosk-mode-validation.md`). |
| M13 | Cmd+Option+Esc | Force Quit | GAP | — | Cannot block (OS-level). | Press Cmd+Option+Esc. | macOS | N/A | Documented limitation. |
| M14 | Ctrl+Cmd+Power | Power dialog | GAP | — | Cannot block. | Trigger combo. | macOS | N/A | Documented limitation. |

## Linux — X11

Code baseline: `agent/src/main/platform/linux.ts` — block list mirrors Windows; `kiosk:true`. `electron#3646`: DE-dependent behavior; verify per DE.

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env (DE) | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| L1 | Alt+F4 | Close window | BLOCKED (app) | `before-input-event` (`linux.ts:19-27,84-98`) | Overlay does not close. | Press Alt+F4. | GNOME/KDE/XFCE | | Verify per-DE. |
| L2 | F12 | DevTools | BLOCKED (app) | input trap + `devTools:false` | No DevTools. | Press F12. | per-DE | | |
| L3 | Ctrl+Shift+I | DevTools | BLOCKED (app) | input trap | No DevTools. | Press Ctrl+Shift+I. | per-DE | | |
| L4 | Alt+Shift+I | DevTools | BLOCKED (app) | input trap | No DevTools. | Press Alt+Shift+I. | per-DE | | |
| L5 | Ctrl+P | Print | BLOCKED (app) | input trap | No print dialog. | Press Ctrl+P. | per-DE | | |
| L6 | F11 | Fullscreen toggle | BLOCKED (app) | input trap | No fullscreen exit. *Observation.* | Press F11. | per-DE | | XFCE: Alt may exit fullscreen (`#3646`). |
| L7 | Escape | Esc | BLOCKED (app) | input trap | No dismiss. *Observation.* | Press Escape. | per-DE | | |
| L8 | Alt+Tab | App switch | GAP / DE-dependent | — | May be suppressed by kiosk on some WMs, not others. | Press Alt+Tab. | per-DE | | Kiosk may not suppress on all WMs (`#3646`). |
| L9 | Ctrl+Alt+Del / Ctrl+Alt+Backspace | OS | GAP | — | OS-level. | Trigger combo. | per-DE | | |
| L10 | Compositor exit (Alt exits fullscreen on XFCE) | WM-specific | GAP / DE-dependent | — | DE-dependent. | Reproduce per DE. | per-DE | | Test GNOME/KDE/XFCE/DWM. |

## Linux — Wayland

Code baseline: `agent/src/main/platform/linux.ts` `isWayland()` — applies `setKiosk` + maximize + `alwaysOnTop('screen-saver')` and logs a warning; `electron#50403` (always-on-top non-functional).

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| WL1 | App-level blocks (Alt+F4, F12, Ctrl+Shift+I, Alt+Shift+I, Ctrl+P, F11, Escape) | Input traps | BLOCKED (app) | `before-input-event` (`linux.ts:84-98`) | Where input reaches renderer, no action. | Exercise each. | Wayland (compositor) | | Verify per compositor. |
| WL2 | Window / compositor switch | WM escape | GAP | — | `setAlwaysOnTop` non-functional (`#50403`). | Attempt to switch away. | Wayland | | Remediation: dedicated compositor (Cage / gnome-kiosk / ubuntu-frame). |
| WL3 | Screenshots | Capture | GAP | — | PipeWire portal prompt; fails gracefully. | Trigger server screenshot. | Wayland | | See agent-setup.md Linux note. |

## Discrepancies & observations

- **`Escape` and `F11`** appear in the code `BLOCKED_SHORTCUTS` lists (`windows.ts:24-25`, `linux.ts:24-25`) but are **not** enumerated in the Epic 7.3 todo. They are defensive (prevent fullscreen-exit / stray Esc) and harmless — recorded here as `BLOCKED (app)` observations (rows W6/W7, L6/L7).
- **`Alt+Shift+I`** is an Edge/Chromium-style shortcut, not a standard Electron DevTools binding; blocking it is defensive parity with Windows/Chromium behavior.
- **Windows Alt+F4 backstop:** `ARCH-02` recommends a `close`/`beforeunload` handler as a backstop. Current code relies on `closable:false` + input trap. If W1 ever fails, file a follow-up to add the `close` handler — out of scope for 7.3.

## Verification run log

| Run date | Engineer | Arcade ver | Electron ver | OS / DE / session | Pass | Fail | N/A |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
