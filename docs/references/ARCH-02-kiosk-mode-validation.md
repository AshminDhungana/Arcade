# ARCH-02: Electron `kiosk: true` Validation & Mitigation Reference

Validated against Electron's official docs and issue tracker (checked June 2026). Summary: most of the original checklist's "blocked by default" assumptions do not hold. Treat kiosk mode as a starting point, not a lockdown — each shortcut below needs an explicit app-level mitigation.

---

## Summary table

| Platform | Shortcut | Blocked by `kiosk: true` alone? | Evidence | Mitigation needed |
|---|---|---|---|---|
| Windows | Alt+F4 | ❌ No | Listed as a live kiosk-breakout vector (closes focused window) | `beforeunload`/`close` interception |
| Windows | F12 (DevTools) | ❌ No (and `devTools:false` has gaps) | Breakout reference repo; bypass via popup windows in electron/electron#33694 | `webPreferences.devTools:false` on **every** window incl. popups + `before-input-event` trap |
| Windows | Ctrl+P (Print) | ❌ No | Listed as live breakout vector — can pivot to OS print/file settings | Intercept print shortcut, route through custom print flow |
| Windows | Win+D (show desktop/taskbar) | ❌ No — open bug | electron/electron#38020, reproduced on Electron 23/27/28, Windows 11 22H2, unresolved | No clean fix exists; consider Shell replacement (regedit `Winlogon\Shell`) for true lockdown |
| Windows | Ctrl+Alt+Del | ❌ Cannot be intercepted (by design) | OS-level Secure Attention Sequence — confirmed correct, no userspace app can hook this | None possible — document as permanent limitation |
| macOS | Cmd+Space (Spotlight) | ✅ Yes | Confirmed in electron/electron#18207 | — |
| macOS | Cmd+W (close window) | ✅ Yes | Confirmed in electron/electron#18207 | — |
| macOS | Cmd+Q (quit) | ❌ No | Requires manual override | `globalShortcut.register('Command+Q', ...)` |
| macOS | Cmd+Tab (app switch) | ❌ No — long-standing gap | Open since Electron v5 (2019), still reported on v6/v7+ in same thread | Re-assert kiosk on `blur`, or native `NSApplicationPresentationDisableProcessSwitching` flag |
| macOS | Cmd+Option+Space (Finder search) | ❌ No | Reported as a secondary bypass even when Cmd+Space is blocked | Same blur-handler approach |
| Linux (X11) | Compositor shortcuts | ⚠️ Inconsistent | electron/electron#3646: works differently per DE; DevTools openable, Alt exits fullscreen on XFCE; kiosk mode reportedly non-functional under some WMs (e.g. DWM-style) | Test per target DE explicitly; don't assume parity across GNOME/KDE/XFCE |
| Linux (Wayland) | `setAlwaysOnTop(true, 'screen-saver')` fallback | ❌ Non-functional | Electron docs: "Not supported on Wayland (Linux)"; open bug electron/electron#50403 (reproduced, `isAlwaysOnTop()` even misreports state) | No working Electron-level fallback currently exists; investigate compositor-specific layer-shell/session-lock protocols outside Electron |

---

## Mitigation code stubs

### 1. Windows: globalShortcut overrides + close interception

```js
const { app, globalShortcut, BrowserWindow } = require('electron')

function registerKioskShortcutBlocks(win) {
  // Alt+F4 cannot be reliably caught via globalShortcut (it's handled by the
  // OS window manager before Electron sees it in many configurations), so
  // the close/beforeunload path is the more reliable backstop:
  win.on('close', (e) => {
    if (!appIsQuitting) {
      e.preventDefault()
    }
  })

  // Block common print/devtools accelerators app-wide while focused
  win.webContents.on('before-input-event', (event, input) => {
    const blockedKeys = ['F12', 'p'] // Ctrl+P comes through with input.control
    if (input.key === 'F12') {
      event.preventDefault()
    }
    if (input.control && input.key.toLowerCase() === 'p') {
      event.preventDefault()
    }
  })
}
```

> Note: per electron/electron#33694, `devTools:false` and accelerator blocks can be bypassed in **secondary windows** created via `setWindowOpenHandler`. Apply the same `before-input-event` trap and `webPreferences.devTools:false` to every `BrowserWindow` your app creates, not just the main one.

For Win+D / taskbar exposure, there is no supported Electron fix today (electron/electron#38020 is open and unresolved across multiple versions). If taskbar suppression is a hard requirement, the realistic options are:
- Replace `explorer.exe` as the shell via `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\Shell` (Windows-only, requires deployment control of the device)
- Accept the gap and document it as a known limitation for unmanaged/BYOD deployments

### 2. macOS: Cmd+Q override + Cmd+Tab re-assertion

```js
const { app, globalShortcut, BrowserWindow } = require('electron')

function registerMacKioskOverrides(win) {
  // Cmd+Q is not blocked by kiosk mode by default
  globalShortcut.register('Command+Q', () => {
    // no-op, or route to your own confirm-and-quit flow
  })

  // Cmd+Tab / Cmd+Option+Space are not interceptable via globalShortcut
  // (they're handled by the OS window server). The common workaround is to
  // re-assert kiosk state when the window loses focus:
  win.on('blur', () => {
    win.hide()
    win.setKiosk(false)
    win.moveTop()
    win.focus()
    win.setKiosk(true)
    win.show()
    win.focus()
  })
}
```

> For a more robust fix than the `blur` re-assertion hack, some teams set the private AppKit flag `NSApplicationPresentationDisableProcessSwitching` via a small native (Objective-C/Swift) helper invoked from Electron — this isn't exposed through Electron's JS API, so it requires a native module or `app.dock`-level native shim. Treat this as a "if the blur hack isn't tight enough" escalation, not a first resort.

### 3. Linux (X11): per-DE test matrix

There's no single code fix here — the gap is environmental. Recommend testing kiosk behavior explicitly against each DE you intend to support rather than assuming one result generalizes:

```markdown
- [ ] GNOME (X11 session) — test DevTools, Alt+Tab, fullscreen-exit
- [ ] KDE Plasma (X11) — same
- [ ] XFCE — known issue: Alt key can exit fullscreen (electron/electron#3646)
- [ ] Any DWM-style/tiling WM you plan to support — kiosk mode reported non-functional in some configs
```

### 4. Linux (Wayland): don't rely on `setAlwaysOnTop`

```js
// This does NOT work reliably on Wayland — confirmed non-functional,
// tracked in electron/electron#50403. Do not treat this as your fallback.
win.setAlwaysOnTop(true, 'screen-saver') // ⚠️ no effect on Wayland
```

Until upstream Electron support improves, options are:
- Pin deployment to an X11 session (XWayland or disable Wayland) where the above mitigations at least partially work
- Investigate compositor-native layer-shell or session-lock protocols (e.g. `wlr-layer-shell`, GNOME's session lock) outside of Electron's window APIs — this would require native/platform-specific code, not something Electron's BrowserWindow exposes today
- Explicitly scope Wayland out of supported kiosk targets for this release and revisit when Electron's Wayland support matures

---

## Sources

- electron/electron#3646 — Kiosk mode not working on Linux (X11, compositor-dependent)
- electron/electron#18207 — Kiosk mode still allows Cmd+Tab (macOS)
- electron/electron#33694 — devTools:false bypass via popup/secondary windows
- electron/electron#38020 — setAlwaysOnTop('screen-saver') doesn't stop Windows taskbar (Win+D)
- electron/electron#50403 — setAlwaysOnTop has no effect under Wayland
- ikarus23/kiosk-mode-breakout — reference list of general kiosk-breakout shortcuts (Alt+F4, Win+D, F12, Ctrl+P, Shift x5/Sticky Keys, etc.)
- Electron official docs — `BrowserWindow` API, `WebPreferences` (`devTools` option, Wayland support notes)
