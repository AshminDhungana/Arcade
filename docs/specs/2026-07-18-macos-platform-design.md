# Epic 7.1 — macOS Platform Implementation (`macos.ts`)

- **Date:** 2026-07-18
- **Epic:** 7.1 macOS Platform Implementation (ENG-A)
- **Component:** `agent/` (Electron agent, `src/main/platform/`)
- **Status:** Design approved — pending implementation plan
- **Source docs:** `docs/Arcade_SDD.md` (§7.1–§7.5), `docs/TODO.md` (ARCH-02, Epic 7.1), `CLAUDE.md`

## Goal

Provide a complete macOS implementation of the agent's `IPlatformService`
abstraction so the Electron agent runs as a kiosk on macOS with the same
behavior as Windows: full-screen overlay access control, in-game HUD, system
restart/shutdown, screenshots, and login auto-start.

## Scope (decided)

**Implement the full 14-method `IPlatformService` interface**, mirroring
`windows.ts` method-for-method. The Epic 7.1 task listed only 6 methods, but
the interface (`agent/src/main/platform/types.ts:65`) requires 14. The
missing 8 (`showHud`, `hideHud`, `showLowTimeWarning`, `updateTimer`,
`sendAnnouncement`, `isKioskVisible`, `getSystemInfo`, plus the kiosk/HUD
window plumbing) all exist in `windows.ts` and are mandatory for `macos.ts` to
compile against the interface and behave correctly at runtime.

No shared base module is introduced — `macos.ts` is a deliberate mirror of
`windows.ts` so both stay independently readable. `linux.ts` (ENG-B, Phase 7)
will follow the same shape later.

### Non-goals

- No Linux implementation (separate task).
- No electron-builder / `.dmg` packaging or code-signing/notarization (Phase 11).
  The Screen Recording **entitlement** is flagged here but implemented there.
- No changes to the `IPlatformService` interface or the renderer.

## Context

- `agent/src/main/platform/types.ts` defines `IPlatformService` (14 methods)
  and `OverlayContent` / `SystemInfo`.
- `agent/src/main/platform/windows.ts` is the reference implementation; the macOS
  class copies its window/IPC logic and swaps only the OS-specific bodies.
- `agent/src/main/platform/index.ts` factory currently only imports `windows.js`
  and **throws** for `darwin`. It must gain a `darwin` branch. (`PLATFORM_MODULES`
  already maps `darwin: './macos.js'`.)
- `agent/src/main/index.ts` creates the platform service in `bootstrap()` and
  needs **no** macOS-specific edits — shortcut hardening lives inside `macos.ts`.

## File changes

| File | Change |
|---|---|
| `agent/src/main/platform/macos.ts` | **New.** `class MacosPlatformService implements IPlatformService`. |
| `agent/src/main/platform/index.ts` | Add `darwin` import branch (mirror the `win32` branch). |

## Design

### 1. Architecture & method map

`MacosPlatformService` mirrors `windows.ts` structure, swapping OS-specific
bodies. All 14 methods implemented:

| Method | macOS body | Differs from Windows? |
|---|---|---|
| `showKioskOverlay` / `hideKioskOverlay` | `BrowserWindow` kiosk | identical options |
| `showHud` / `hideHud` | transparent `BrowserWindow` + `setIgnoreMouseEvents` | identical |
| `showLowTimeWarning` / `updateTimer` / `sendAnnouncement` / `isKioskVisible` | IPC to active window | identical |
| `restartPC` | `osascript … restart` | **yes** |
| `shutdownPC` | `osascript … shut down` | **yes** |
| `captureScreenshot` | `desktopCapturer` + TCC handling | same flow, macOS failure mode |
| `enableAutoStart` / `disableAutoStart` | LaunchAgent plist | **yes** |
| `getSystemInfo` | `systeminformation` | identical |

### 2. Kiosk & HUD windows

Copied verbatim from `windows.ts` — the `BrowserWindow` options are
OS-agnostic:

- **Kiosk window:** `fullscreen: true`, `kiosk: true`, `alwaysOnTop: true`,
  `frame: false`, `closable: false`, `skipTaskbar: true` (no-op on macOS,
  harmless), `devTools: false`, `contextIsolation: true`, `sandbox: true`,
  `nodeIntegration: false`, `preload: preload.js`, loads `index.html`.
  Right-click context menu prevented; `before-input-event` wired (see §3).
- **HUD window:** `transparent: true`, `frame: false`, `alwaysOnTop: true`,
  `closable: false`, `focusable: false`, `setIgnoreMouseEvents(true, { forward: true })`,
  loads `hud.html`. Same as Windows.

**Insight:** On macOS, `kiosk: true` sets `NSApplicationPresentationOptions`
to hide the **menu bar and Dock** and (per SDD §7.3) blocks `Cmd+Tab` (app
switching) and `Cmd+Space` (Spotlight). Those two are handled by the kiosk flag
itself; we only separately kill `Cmd+Q/H/M`, which the flag does **not** cover.

### 3. Shortcut hardening (hybrid)

Three layers, all owned by `macos.ts`:

1. **Null menu at construction** — `Menu.setApplicationMenu(null)` in the
   constructor removes the app menu, so Quit/Hide/Minimize menu items don't exist.
2. **`globalShortcut` for app-menu shortcuts** — registered whenever a protected
   window (kiosk or HUD) is visible, unregistered when both are hidden:
   ```
   Command+Q, Command+W, Command+H, Command+M,
   F12, CommandOrControl+Shift+I, Alt+Shift+I, CommandOrControl+P
   ```
   Handler is a no-op `() => {}` (consumes and discards). This is what actually
   blocks `Cmd+Q/H/M`, which a per-window `before-input-event` cannot reach
   because they are application-menu accelerators, not renderer input events.
3. **Per-window `before-input-event`** — copied verbatim from `windows.ts`
   (`BLOCKED_SHORTCUTS`: `Alt+F4`, `Alt+Shift+I`, `Control+Shift+I`,
   `Control+P`, `F12`, `F11`, `Escape`) for parity with Windows.

Register/unregister via two private helpers (`hardenShortcuts()` /
`relaxShortcuts()`), called from `showKioskOverlay`/`showHud` (harden) and
`hideKioskOverlay`/`hideHud` (relax). The kiosk↔HUD transition relaxes-then-
hardens, so the agent stays un-quittable throughout a session by design.

**Documented gaps** (code comments, matching TODO ARCH-02): `Cmd+Tab`/`Cmd+Space`
handled by kiosk mode; `Cmd+Opt+Esc` (Force Quit) and `Ctrl+Cmd+Power`
remain OS-interceptable only and are out of scope.

### 4. System commands

**`restartPC()`**
```ts
await execAsync('osascript -e \'tell application "System Events" to restart\'');
```
**`shutdownPC()`**
```ts
await execAsync('osascript -e \'tell application "System Events" to shut down\'');
```
No `sudo` — works in a logged-in GUI session as a normal user. On failure,
log and re-throw a typed `Error` with an actionable message. (`sudo shutdown`
is documented as the headless/root alternative but is **not** used by the GUI
app, per the approved decision.)

**`captureScreenshot()`** — same flow as Windows, with the macOS-specific
failure mode made explicit:
```ts
const sources = await desktopCapturer.getSources({
  types: ['screen'], thumbnailSize: { width: 1280, height: 720 },
});
if (!sources?.length || !sources[0].thumbnail) {
  log.warn('Screenshot failed: no screen sources — Screen Recording permission likely not granted (TCC).');
  throw new Error('Screenshot capture unavailable: Screen Recording permission not granted');
}
// sharp resize -> 1280x720 jpeg q80 -> Buffer (fallback to raw PNG on sharp error)
```
**Packaging note (flagged, not solved here):** a packaged `.app` also needs the
`com.apple.security.device.screen-capture` entitlement; the TCC Screen Recording
prompt appears automatically in dev. That is an electron-builder / Phase 11
concern, but the permission-failure path above is what makes it observable.

### 5. Auto-start & system info

**`enableAutoStart()`** — write a LaunchAgent plist to
`~/Library/LaunchAgents/com.arcade.agent.plist`. The XML generation is a **pure
private function** `buildLaunchAgentPlist(execPath: string): string` (unit-tested,
see §6):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>         <string>com.arcade.agent</string>
    <key>ProgramArguments</key> <array><string>{process.execPath}</string></array>
    <key>RunAtLoad</key>     <true/>
    <key>ProcessType</key>   <string>Interactive</string>
  </dict>
</plist>
```
`process.execPath` resolves correctly in both dev (`electron`) and a packaged
`.app` (the bundle's MacOS binary). `enableAutoStart` writes via
`fs.promises.writeFile`; `disableAutoStart` does `fs.promises.unlink` (swallow
`ENOENT`).

**`getSystemInfo()`** — identical to Windows:
`Promise.all([si.cpu(), si.mem(), si.diskLayout()])`, returns
`osName: process.platform` (`'darwin'`), `osVersion: os.release()`,
`hostname: os.hostname()`. Kept as `process.platform` to match Windows returning
`'win32'`; normalizing to `'macOS'` is a one-line change if the dashboard
expects it (default: parity).

### 6. Error handling, testing, risks

**Error handling:** every OS call logs then re-throws a typed `Error` with an
actionable message:
- `osascript` denied/errored → log + throw.
- screenshot with no sources → warn (TCC) + throw (handled gracefully by the WS
  layer upstream).
- plist write fails (perms) → log + throw; plist delete missing is non-fatal.

**Testing constraint:** the existing CI is Windows/Linux (per `CLAUDE.md` +
`TODO.md`), so real macOS behaviors **cannot run in CI**. Design accordingly:
- **Unit-testable pure logic** (no OS calls): `buildLaunchAgentPlist(execPath)`
  output assertion; `globalShortcut` registration list assertion. Run on any runner.
- **Manual verification checklist** (documented in this spec, executed on a real
  Mac): kiosk shows; `Cmd+Q/H/M/W` blocked; `osascript` restart/shutdown works;
  screenshot succeeds after granting Screen Recording; LaunchAgent loads the app on
  login; HUD overlays a running game with click-through.

**Risks / known gaps:**
1. `osascript` requires a GUI login session — headless/SSH restart unsupported
   (acceptable; matches task scope).
2. Screen Recording TCC + entitlement needed for packaged screenshot.
3. Force Quit (`Cmd+Opt+Esc`) / `Ctrl+Cmd+Power` uninterceptable (documented).
4. `Cmd+Tab`/`Cmd+Space` covered by the kiosk flag, not by our code.

## Interface compliance checklist (all 14)

- [x] `showKioskOverlay(content)` — kiosk `BrowserWindow`
- [x] `hideKioskOverlay()` — destroy + `showHud()`
- [x] `showHud()` — transparent `BrowserWindow` + click-through
- [x] `hideHud()` — destroy
- [x] `showLowTimeWarning(minutes)` — IPC to active window
- [x] `updateTimer({ elapsedSeconds })` — IPC to active window
- [x] `sendAnnouncement(text, durationMs)` — IPC to active window
- [x] `isKioskVisible()` — window visible check
- [x] `restartPC()` — `osascript … restart`
- [x] `shutdownPC()` — `osascript … shut down`
- [x] `captureScreenshot()` — `desktopCapturer` + TCC handling
- [x] `enableAutoStart()` — LaunchAgent plist write
- [x] `disableAutoStart()` — LaunchAgent plist delete
- [x] `getSystemInfo()` — `systeminformation`

## Open decisions (defaults chosen)

- `osName` returned as `process.platform` (`'darwin'`) — parity with Windows.
  Flip to `'macOS'` if the dashboard keys off a friendly name.
- LaunchAgent `Label` = `com.arcade.agent` (per Epic 7.1 task), independent of
  the electron-builder `appId` (`com.neurotech.arcade.agent`).
