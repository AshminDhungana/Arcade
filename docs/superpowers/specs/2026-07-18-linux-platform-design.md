# Linux Platform Implementation (`linux.ts`) — Design Spec

- **Date:** 2026-07-18
- **Epic:** Phase 7 — Cross-Platform Agent Polish (Epic 7.2: Linux Platform Implementation, ENG-B)
- **TODO item:** `Task: Implement linux.ts` (`docs/TODO.md`, ~line 1436) + factory wiring in `agent/src/main/platform/index.ts`
- **Status:** Approved design, pending implementation

## Goal

Implement `agent/src/main/platform/linux.ts` so the Arcade Electron agent runs on
Linux as a first-class platform, satisfying `IPlatformService` (all 14 methods) and
the Epic 7.2 task bullets:

1. `showKioskOverlay()` / `hideKioskOverlay()` — `setKiosk(true/false)`, with a Wayland fallback
2. `restartPC()` — `systemctl reboot`
3. `shutdownPC()` — `systemctl poweroff`
4. `captureScreenshot()` — `desktopCapturer` (X11 native; graceful on Wayland)
5. `enableAutoStart()` — write `~/.config/autostart/arcade-agent.desktop`
6. `disableAutoStart()` — delete that `.desktop` file

Plus the 8 remaining `IPlatformService` methods (HUD, timer, announcement, low-time,
visibility, system info), which mirror `windows.ts`.

## Decisions (from brainstorming)

| Decision | Choice | Rationale |
| --- | --- | --- |
| Wayland kiosk strategy | Implement the task's flags (`setKiosk` + maximise + `setAlwaysOnTop('screen-saver')`) **and** log a loud warning + document the compositor recipe | Reconciles the Epic 7.2 task with ARCH-02: the `screen-saver` flag is cosmetic on Wayland (confirmed by research), not a security control. Refusing Wayland entirely would break the agent on Wayland sessions. |
| Recommended session | X11 for client PCs (per R-02) | Kiosk lockdown is reliable on X11; Wayland requires a dedicated kiosk compositor for true lockdown. |
| Power control primary | `systemctl reboot` / `systemctl poweroff` (literal task) | Matches the task exactly. |
| Power control fallback | `loginctl reboot` / `loginctl poweroff` on `systemctl` rejection | Session-scoped, no root needed on most distros; improves reliability. **Approved as included.** |
| Screenshot on Wayland | Throw a clear, catchable `Error` when no sources returned | "Graceful" = upstream `TAKE_SCREENSHOT` path already reports capture failures; don't silently return junk. |
| Auto-start mechanism | XDG autostart `.desktop` at `~/.config/autostart/` (literal task) | User-session autostart; matches task. systemd `--user` `.service` left to sibling task (TODO line 1447). |
| `darwin` factory branch | Left throwing (no-op) | `macos.ts` was removed from its branch (orphaned at `54256ca`); not in scope for ENG-B 7.2. |
| Tests | Mirror `windows.test.ts` mocking, swap `exec` mock for `fs/promises` mock on autostart | Reuses the established, proven test pattern. |

## Context

- `agent/src/main/platform/types.ts` defines `IPlatformService` with **14 methods**:
  `showKioskOverlay`, `hideKioskOverlay`, `showHud`, `hideHud`, `showLowTimeWarning`,
  `updateTimer`, `sendAnnouncement`, `isKioskVisible`, `restartPC`, `shutdownPC`,
  `captureScreenshot`, `enableAutoStart`, `disableAutoStart`, `getSystemInfo`.
  `linux.ts` must implement all 14 or TypeScript compilation fails.
- `agent/src/main/platform/windows.ts` is the canonical full implementation and the
  template to mirror. macOS "mirrors `windows.ts`" (per TODO 7.1).
- `agent/src/main/platform/index.ts` `getPlatformService()` currently only handles
  `win32` and throws for `darwin`/`linux` (the `PLATFORM_MODULES` map already lists
  `linux: './linux.js'`).
- `agent/src/main/ws/commands.ts` `TAKE_SCREENSHOT` handler delegates capture to the
  WS client, which calls `platform.captureScreenshot()`. A thrown error there is
  reported back to the server — so "graceful" handling = throw a descriptive error.
- `agent/tests/platform/windows.test.ts` establishes the mocking pattern
  (`vi.mock('electron')` with `MockBrowserWindow` + `desktopCapturer`,
  `vi.mock('sharp')`, `vi.mock('systeminformation')`, `vi.mock('child_process')`).
  Autostart on Linux uses `node:fs/promises`, not `exec`, so the Linux test mocks `fs`.

### Research findings (why the Wayland fallback is not a security control)

- Wayland compositors own window stacking/focus; no Electron app-level API
  (`setKiosk`, `setAlwaysOnTop`, `before-input-event`, `globalShortcut`) can prevent
  the user from switching away. Secure Wayland kiosk = dedicated single-app compositor
  (Cage, gnome-kiosk, ubuntu-frame).
- Electron 38.2+ is Wayland-native; `setKiosk(true)` *renders* fullscreen on Wayland
  but is not bypass-proof there.
- `desktopCapturer` on Wayland uses PipeWire/portals — restricted, requires a
  user-granted prompt, inconsistent vs X11. Empty source list → throw.
- Wayland detection: `XDG_SESSION_TYPE === 'wayland'` or `WAYLAND_DISPLAY` set.

## Design

### 1. New file: `agent/src/main/platform/linux.ts`

```ts
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promises as fs } from 'node:fs';
import os from 'os';
import { BrowserWindow, desktopCapturer } from 'electron';
import { exec } from 'child_process';
import { promisify } from 'util';
import sharp from 'sharp';
import si from 'systeminformation';
import type { IPlatformService, OverlayContent, SystemInfo } from './types.js';

const execAsync = promisify(exec);

const APP_NAME = 'ArcadeAgent';
const AUTO_START_DIR = path.join(os.homedir(), '.config', 'autostart');
const AUTO_START_FILE = path.join(AUTO_START_DIR, 'arcade-agent.desktop');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BLOCKED_SHORTCUTS = [
  'Alt+F4', 'Alt+Shift+I', 'Control+Shift+I', 'Control+P', 'F12', 'F11', 'Escape',
];

/** True when running under a native Wayland session. */
function isWayland(): boolean {
  return process.env.XDG_SESSION_TYPE === 'wayland' || Boolean(process.env.WAYLAND_DISPLAY);
}
```

`class LinuxPlatformService implements IPlatformService` with the same private fields
as `windows.ts` (`kioskWindow`, `hudWindow`, `sessionActive`).

### 2. Kiosk overlay + Wayland handling (Section B)

- `showKioskOverlay(content)`: mirror `windows.ts` — create `BrowserWindow`
  (`fullscreen: true, kiosk: true, alwaysOnTop: true, frame: false, closable: false,
  skipTaskbar: true`, `webPreferences` identical to `windows.ts`), block context menu
  and `before-input-event` shortcuts with the same `BLOCKED_SHORTCUTS`, load
  `../../renderer/index.html`, `send('overlay:update', content)` on `did-finish-load`.
- **Wayland addition:** at the top of `showKioskOverlay`, after creating the window,
  if `isWayland()`:
  ```ts
  win.setKiosk(true);
  win.maximize();
  win.setAlwaysOnTop(true, 'screen-saver');
  console.warn(
    '[linux] Wayland detected: kiosk overlay is NOT bypass-proof. ' +
    'Deploy under a Wayland kiosk compositor (Cage / gnome-kiosk / ubuntu-frame) ' +
    'for true lockdown. See docs/agent-setup.md.',
  );
  ```
  (`windows.ts` uses no logger, so `console.warn` matches that convention.)
- `hideKioskOverlay()`: mirror `windows.ts` — hide + destroy kiosk window, set
  `sessionActive = true`, `showHud()`.

X11 behavior is unchanged from the Windows implementation.

### 3. Power control (Section C)

```ts
async restartPC(): Promise<void> {
  try {
    await execAsync('systemctl reboot');
  } catch {
    await execAsync('loginctl reboot');
  }
}

async shutdownPC(): Promise<void> {
  try {
    await execAsync('systemctl poweroff');
  } catch {
    await execAsync('loginctl poweroff');
  }
}
```

If both fail, the final rejection propagates as a clear error (operator configures
polkit / runs as a user with shutdown rights).

### 4. Screenshot (Section D)

Mirror `windows.ts`: `desktopCapturer.getSources({ types: ['screen'], thumbnailSize:
{ width: 1280, height: 720 } })` → `sharp(...).resize(1280, 720, { fit: 'inside',
withoutEnlargement: true }).jpeg({ quality: 80 }).toBuffer()`, raw PNG fallback on
sharp failure. **Add** at the no-sources guard:

```ts
if (!sources || sources.length === 0) {
  throw new Error(
    'Screenshot unavailable on this session (no screen sources; Wayland/PipeWire ' +
    'portal not permitted or X11 display absent).',
  );
}
```

### 5. Auto-start via `.desktop` (Section E)

```ts
async enableAutoStart(): Promise<void> {
  const desktopEntry = [
    '[Desktop Entry]',
    'Type=Application',
    'Name=Arcade Agent',
    `Exec=${process.execPath}`,
    'X-GNOME-Autostart-enabled=true',
    'X-GNOME-Autostart-Delay=5',
    '',
  ].join('\n');
  await fs.mkdir(AUTO_START_DIR, { recursive: true });
  await fs.writeFile(AUTO_START_FILE, desktopEntry, { mode: 0o644 });
}

async disableAutoStart(): Promise<void> {
  await fs.rm(AUTO_START_FILE, { force: true });
}
```

`fs.rm({ force: true })` makes disable idempotent (no-op if the file is absent).

### 6. Remaining methods (Section A/F — mirror `windows.ts`)

- `showHud()` / `hideHud()`: transparent, `alwaysOnTop`, `setIgnoreMouseEvents(true,
  { forward: true })` HUD window — identical to `windows.ts`. (Resolves the
  "HUD window is Windows-first (Linux factory throws - pending Epic 7.2)" gap noted at
  TODO ~line 1191.)
- `showLowTimeWarning(minutes)`, `isKioskVisible()`, `updateTimer({ elapsedSeconds })`,
  `sendAnnouncement(text, durationMs)`: route to the active window
  (`hudWindow` when `sessionActive`, else `kioskWindow`); no-op if not visible.
- `getSystemInfo()`: identical `systeminformation` call (`cpu`, `mem`, `diskLayout`)
  as `windows.ts`; `osName: process.platform`, `osVersion: os.release()`,
  `hostname: os.hostname()`, rounded GB.

### 7. Factory wiring (`agent/src/main/platform/index.ts`)

Add a `linux` branch to `getPlatformService()` after the existing `win32` branch:

```ts
if (platform === 'linux') {
  const { LinuxPlatformService } = await import('./linux.js');
  return new LinuxPlatformService();
}
```

Leave the `darwin` throw as-is (its `macos.ts` is not present in this tree).

### 8. Tests — `agent/tests/platform/linux.test.ts`

Mirror `windows.test.ts` mocking strategy:
- `vi.mock('electron')` → `MockBrowserWindow` + `desktopCapturer.getSources` resolving
  one fake source (and a second case resolving `[]` to assert the Wayland/no-source
  error).
- `vi.mock('sharp')`, `vi.mock('systeminformation')`, `vi.mock('child_process')`
  (for restart/shutdown assertions).
- **`vi.mock('node:fs')`** → return `{ promises: { mkdir: vi.fn(), writeFile:
  vi.fn(), rm: vi.fn() } }` to assert autostart write/delete (replaces the registry
  `exec` assertions used on Windows). The code imports `promises` off `'node:fs'`, so
  mocking that module intercepts the calls.

Cases:
1. All **14** `IPlatformService` methods exist (include `isKioskVisible`).
2. `restartPC()` calls `systemctl reboot`; `shutdownPC()` calls `systemctl poweroff`.
3. `captureScreenshot()` returns a `Buffer`; and throwing when `getSources` resolves `[]`.
4. `enableAutoStart()` writes `arcade-agent.desktop` into `~/.config/autostart/`;
   `disableAutoStart()` calls `rm` on it.
5. `getSystemInfo()` returns the expected shape.
6. `isWayland()` returns `true` when `XDG_SESSION_TYPE==='wayland'`, `false` otherwise
   (set/clear `process.env` in the test).

### 9. Docs — `docs/agent-setup.md`

Add a **Linux** subsection:
- X11 is the recommended session for client PCs (reliable kiosk lockdown; R-02).
- Wayland: the overlay is only bypass-proof when launched under a dedicated kiosk
  compositor. Provide a minimal **Cage** recipe
  (`cage /path/to/arcade-agent --ozone-platform-hint=auto`) and mention gnome-kiosk /
  ubuntu-frame as alternatives.
- XDG autostart: the agent writes `~/.config/autostart/arcade-agent.desktop`
  automatically when auto-start is enabled from the dashboard; document the path and
  how to remove it manually.

## Testing

- `npx vitest run tests/platform/linux.test.ts` — new suite (target ~9 cases above).
- `npx tsc -p tsconfig.main.json --noEmit` — `linux.ts` satisfies `IPlatformService`.
- `npm run lint` in `agent/` — clean.
- Manual (per Phase 7 checklist, on real Linux hardware / VM): kiosk overlay shows;
  restart/shutdown work (use a VM to avoid disrupting the dev machine); screenshot on
  X11 succeeds; auto-start `.desktop` appears in `~/.config/autostart/` and the agent
  launches on next login.

## Out of scope (sibling TODO tasks)

- `docs/autostart/arcade-agent.service` (systemd `--user`) + `arcade-agent.desktop`
  template (TODO line 1447) — runtime autostart is covered here; the template/doc
  files are a separate task.
- `electron-builder.yml` Linux targets `AppImage` + `deb` and `npm run build -- --linux`
  (TODO lines 1444–1446).
- macOS `darwin` factory branch (orphaned `macos.ts`).

## Risks

- **Wayland bypass (R-02):** On a native Wayland session without a kiosk compositor,
  the overlay can be switched away from. Mitigated by the loud warning + the
  X11/Cage recommendation in `docs/agent-setup.md`.
- **`systemctl` permission:** A user without polkit shutdown rights gets a rejection;
  the `loginctl` fallback covers most desktop sessions, otherwise the operator grants
  rights. Surfaced via the thrown error.
- **Wayland screenshot:** Requires the PipeWire portal prompt; on headless/denied
  sessions capture throws (handled gracefully upstream).
