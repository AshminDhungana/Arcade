# Epic 7.1 macOS Platform Implementation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `agent/src/main/platform/macos.ts` as a complete `IPlatformService` (all 14 methods) mirroring `windows.ts`, wire it into the platform factory, and verify it with unit tests that run on the existing Windows/Linux CI.

**Architecture:** `MacosPlatformService` is a drop-in mirror of `WindowsPlatformService`. OS-specific bodies are swapped: `osascript` for restart/shutdown, a LaunchAgent plist for auto-start, `globalShortcut` + `Menu.setApplicationMenu(null)` for kiosk hardening (because `Cmd+Q/H/M` are app-menu accelerators that per-window `before-input-event` cannot reach), and TCC-aware `desktopCapturer` handling for screenshots. The factory gains a `darwin` branch.

**Tech Stack:** TypeScript (Electron main process, ESM), `vitest` (node env), `electron` (mocked in tests), `sharp`, `systeminformation`.

> **Location note:** The writing-plans default `docs/superpowers/plans/` is gitignored in this repo, so this plan lives alongside the spec at `docs/specs/2026-07-18-macos-platform-plan.md`.

## Global Constraints

- Implement the **full 14-method `IPlatformService`** — do **not** introduce a shared base class; mirror `windows.ts` and swap only OS-specific bodies.
- Kiosk/HUD `BrowserWindow` options are OS-agnostic — copy `windows.ts` verbatim for those.
- Shortcut hardening is **hybrid**: `Menu.setApplicationMenu(null)` in the constructor + `globalShortcut.registerAll` for `Command+Q`, `Command+W`, `Command+H`, `Command+M`, `F12`, `CommandOrControl+Shift+I`, `Alt+Shift+I`, `CommandOrControl+P` (registered while a protected window is visible, unregistered when both are hidden) **plus** per-window `before-input-event` mirroring `windows.ts` `BLOCKED_SHORTCUTS`.
- `restartPC` / `shutdownPC` use **`osascript`** (no `sudo`): `tell application "System Events" to restart` / `shut down`.
- `enableAutoStart` writes a LaunchAgent plist to `~/Library/LaunchAgents/com.arcade.agent.plist` with `ProgramArguments: [process.execPath]`, `RunAtLoad: true`, `ProcessType: Interactive`; `disableAutoStart` deletes it (swallow `ENOENT`).
- `captureScreenshot` is TCC-aware: throw a clear `Error` (and `console.warn`) when no screen sources are returned (Screen Recording permission not granted).
- CI is Windows/Linux: real macOS behaviors are verified **manually** (checklist in Task 3); pure logic is unit-tested via mocked `electron`.
- Commit convention: conventional commits, one commit per task.
- Import style: ESM with explicit `.js` extensions (e.g. `from './types.js'`), matching `windows.ts`.

## File Structure

| File | Responsibility |
|---|---|
| `agent/src/main/platform/macos.ts` (new) | `class MacosPlatformService implements IPlatformService` — all 14 methods, macOS-specific bodies. |
| `agent/src/main/platform/index.ts` (modify) | Add `darwin` dynamic-import branch so `getPlatformService()` returns `MacosPlatformService`. |
| `agent/tests/platform/macos.test.ts` (new) | Unit tests for `MacosPlatformService` (mocked electron/fs/sharp/systeminformation). |
| `agent/tests/platform/factory.test.ts` (modify) | Add a `darwin` case; extend the electron mock with `Menu` + `globalShortcut`. |

---

### Task 1: Implement `MacosPlatformService` + unit tests

**Files:**
- Create: `agent/src/main/platform/macos.ts`
- Create: `agent/tests/platform/macos.test.ts`

**Interfaces:**
- Consumes: `IPlatformService`, `OverlayContent`, `SystemInfo` from `./types.js` (already defined).
- Produces: `class MacosPlatformService` (named export) — used by `index.ts` in Task 2 and imported by `macos.test.ts`.

- [ ] **Step 1: Write the failing test** (`agent/tests/platform/macos.test.ts`)

Create the test file with mocked `electron`, `child_process`, `sharp`, `systeminformation`, and `node:fs`. The mock captures the `before-input-event` handler so it can be fired.

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const handlers: Record<string, (...args: any[]) => void> = {};
const mockWebContents = {
  on: vi.fn((event: string, cb: (...a: any[]) => void) => { handlers[event] = cb; }),
  once: vi.fn(),
  send: vi.fn(),
  loadFile: vi.fn(),
  loadURL: vi.fn(),
};
const preventDefault = vi.fn();

vi.mock('electron', async () => {
  const actual = await vi.importActual<typeof import('electron')>('electron');
  class MockBrowserWindow {
    webContents = mockWebContents;
    show = vi.fn();
    hide = vi.fn();
    destroy = vi.fn();
    loadFile = vi.fn();
    setIgnoreMouseEvents = vi.fn();
    isDestroyed = vi.fn().mockReturnValue(false);
    isVisible = vi.fn().mockReturnValue(true);
    on = vi.fn();
    constructor(_opts?: Record<string, unknown>) {}
  }
  return {
    ...actual,
    BrowserWindow: MockBrowserWindow,
    desktopCapturer: {
      getSources: vi.fn().mockResolvedValue([
        {
          id: 'screen:0:0',
          name: 'Screen 1',
          thumbnail: { toPNG: vi.fn().mockReturnValue(Buffer.from('fake-png')) },
        },
      ]),
    },
    globalShortcut: { registerAll: vi.fn(), unregisterAll: vi.fn() },
    Menu: { setApplicationMenu: vi.fn() },
  };
});

vi.mock('child_process', () => ({
  exec: vi.fn().mockImplementation((_cmd: string, _opts: unknown, cb?: (e: unknown, so: string, se: string) => void) => {
    cb?.(null, 'stdout', '');
    return undefined;
  }),
}));

vi.mock('sharp', () => ({
  default: vi.fn().mockReturnValue({
    resize: vi.fn().mockReturnThis(),
    jpeg: vi.fn().mockReturnThis(),
    toBuffer: vi.fn().mockResolvedValue(Buffer.from('compressed-jpg')),
  }),
}));

vi.mock('systeminformation', () => ({
  default: {
    cpu: vi.fn().mockResolvedValue({ brand: 'Intel i7', cores: 8 }),
    mem: vi.fn().mockResolvedValue({ total: 34359738368 }),
    diskLayout: vi.fn().mockResolvedValue([{ size: 1000000000000 }]),
  },
}));

vi.mock('node:fs', () => ({
  promises: {
    writeFile: vi.fn().mockResolvedValue(undefined),
    unlink: vi.fn().mockResolvedValue(undefined),
  },
}));

import { MacosPlatformService } from '../../src/main/platform/macos.js';
import { globalShortcut, Menu, desktopCapturer } from 'electron';
import { exec } from 'child_process';
import * as fsp from 'node:fs';

const OVERLAY = { cafeName: 'C', announcements: [], callStaffEnabled: false, sessionActive: false };

describe('MacosPlatformService', () => {
  let service: MacosPlatformService;

  beforeEach(() => {
    service = new MacosPlatformService();
    vi.clearAllMocks();
    for (const k of Object.keys(handlers)) delete handlers[k];
  });

  afterEach(() => {
    service.hideKioskOverlay();
  });

  it('calls Menu.setApplicationMenu(null) in constructor', () => {
    const svc = new MacosPlatformService();
    expect(Menu.setApplicationMenu).toHaveBeenCalledWith(null);
  });

  it('exposes all IPlatformService methods', () => {
    const expected = [
      'showKioskOverlay', 'hideKioskOverlay', 'showHud', 'hideHud',
      'showLowTimeWarning', 'updateTimer', 'sendAnnouncement', 'isKioskVisible',
      'restartPC', 'shutdownPC', 'captureScreenshot',
      'enableAutoStart', 'disableAutoStart', 'getSystemInfo',
    ];
    for (const m of expected) {
      expect(typeof (service as Record<string, unknown>)[m]).toBe('function');
    }
  });

  it('registers global shortcuts on showKioskOverlay', () => {
    service.showKioskOverlay(OVERLAY);
    expect(globalShortcut.registerAll).toHaveBeenCalledWith(
      expect.arrayContaining(['Command+Q', 'Command+W', 'Command+H', 'Command+M']),
      expect.any(Function),
    );
  });

  it('unregisters global shortcuts on hideKioskOverlay', () => {
    service.showKioskOverlay(OVERLAY);
    service.hideKioskOverlay();
    expect(globalShortcut.unregisterAll).toHaveBeenCalled();
  });

  it('prevents blocked per-window shortcuts via before-input-event', () => {
    service.showKioskOverlay(OVERLAY);
    const handler = handlers['before-input-event'];
    expect(handler).toBeTypeOf('function');
    handler({ preventDefault }, { alt: true, control: false, shift: false, meta: false, key: 'F4' });
    expect(preventDefault).toHaveBeenCalled();
  });

  it('starts restart via osascript', async () => {
    await service.restartPC();
    expect(exec).toHaveBeenCalledWith(
      expect.stringContaining('tell application "System Events" to restart'),
      expect.any(Function),
    );
  });

  it('shuts down via osascript', async () => {
    await service.shutdownPC();
    expect(exec).toHaveBeenCalledWith(
      expect.stringContaining('tell application "System Events" to shut down'),
      expect.any(Function),
    );
  });

  it('returns a Buffer from captureScreenshot', async () => {
    const result = await service.captureScreenshot();
    expect(Buffer.isBuffer(result)).toBe(true);
  });

  it('throws when no screen sources (TCC permission missing)', async () => {
    vi.mocked(desktopCapturer.getSources).mockResolvedValueOnce([]);
    await expect(service.captureScreenshot()).rejects.toThrow(/Screen Recording permission/);
  });

  it('writes a LaunchAgent plist on enableAutoStart', async () => {
    await service.enableAutoStart();
    expect(fsp.writeFile).toHaveBeenCalledWith(
      expect.stringContaining('Library/LaunchAgents/com.arcade.agent.plist'),
      expect.stringContaining('<string>com.arcade.agent</string>'),
    );
    const xml = (fsp.writeFile as any).mock.calls[0][1] as string;
    expect(xml).toContain(`<string>${process.execPath}</string>`);
    expect(xml).toContain('<key>RunAtLoad</key>');
    expect(xml).toContain('<key>ProcessType</key>');
    expect(xml).toContain('<string>Interactive</string>');
  });

  it('removes the LaunchAgent plist on disableAutoStart', async () => {
    await service.disableAutoStart();
    expect(fsp.unlink).toHaveBeenCalledWith(
      expect.stringContaining('com.arcade.agent.plist'),
    );
  });

  it('disableAutoStart swallows ENOENT', async () => {
    (fsp.unlink as any).mockRejectedValueOnce(Object.assign(new Error('nope'), { code: 'ENOENT' }));
    await expect(service.disableAutoStart()).resolves.toBeUndefined();
  });

  it('getSystemInfo returns expected shape', async () => {
    const info = await service.getSystemInfo();
    for (const p of ['cpuModel', 'cpuCores', 'totalMemoryGB', 'totalDiskGB', 'osName', 'osVersion', 'hostname']) {
      expect(info).toHaveProperty(p);
    }
  });

  it('updateTimer sends overlay:timer to the active window', () => {
    service.showKioskOverlay(OVERLAY);
    service.updateTimer({ elapsedSeconds: 42 });
    expect(mockWebContents.send).toHaveBeenCalledWith('overlay:timer', { elapsedSeconds: 42 });
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd agent && npx vitest run tests/platform/macos.test.ts`
Expected: FAIL — `Failed to resolve import "../../src/main/platform/macos.js"`.

- [ ] **Step 3: Write the minimal implementation** (`agent/src/main/platform/macos.ts`)

```ts
import * as path from 'node:path';
import * as os from 'node:os';
import { promises as fsp } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  BrowserWindow,
  desktopCapturer,
  globalShortcut,
  Menu,
} from 'electron';
import { exec } from 'child_process';
import { promisify } from 'util';
import sharp from 'sharp';
import si from 'systeminformation';
import type { IPlatformService, OverlayContent, SystemInfo } from './types.js';

const execAsync = promisify(exec);

const LAUNCH_AGENT_LABEL = 'com.arcade.agent';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Per-window blocked shortcuts (mirrors windows.ts). These are renderer input
// events. macOS app-menu accelerators (Cmd+Q/H/M) are handled by globalShortcut.
const BLOCKED_SHORTCUTS = [
  'Alt+F4',
  'Alt+Shift+I',
  'Control+Shift+I',
  'Control+P',
  'F12',
  'F11',
  'Escape',
];

// App-menu accelerators that before-input-event cannot intercept on macOS.
const GLOBAL_SHORTCUTS = [
  'Command+Q',
  'Command+W',
  'Command+H',
  'Command+M',
  'F12',
  'CommandOrControl+Shift+I',
  'Alt+Shift+I',
  'CommandOrControl+P',
];

const LAUNCH_AGENT_DIR = path.join(os.homedir(), 'Library', 'LaunchAgents');

export class MacosPlatformService implements IPlatformService {
  private kioskWindow: BrowserWindow | null = null;
  private hudWindow: BrowserWindow | null = null;
  private sessionActive = false;

  constructor() {
    // Remove the application menu so Quit/Hide/Minimize menu items don't exist.
    Menu.setApplicationMenu(null);
  }

  showKioskOverlay(content: OverlayContent): void {
    this.sessionActive = false;
    this.hideHud();
    this.hardenShortcuts();
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.show();
      this.kioskWindow.webContents.send('overlay:update', content);
      return;
    }

    const preloadPath = path.join(__dirname, '../../renderer/preload.js');

    this.kioskWindow = new BrowserWindow({
      fullscreen: true,
      kiosk: true,
      alwaysOnTop: true,
      frame: false,
      closable: false,
      skipTaskbar: true,
      webPreferences: {
        devTools: false,
        contextIsolation: true,
        sandbox: true,
        nodeIntegration: false,
        preload: preloadPath,
      },
    });

    this.kioskWindow.webContents.on('context-menu', (event) => {
      event.preventDefault();
    });

    this.kioskWindow.webContents.on('before-input-event', (event, input) => {
      const shortcut = [
        input.alt ? 'Alt' : '',
        input.control ? 'Control' : '',
        input.shift ? 'Shift' : '',
        input.meta ? 'Meta' : '',
        input.key,
      ]
        .filter(Boolean)
        .join('+');

      if (BLOCKED_SHORTCUTS.includes(shortcut)) {
        event.preventDefault();
      }
    });

    this.kioskWindow.on('closed', () => {
      this.kioskWindow = null;
    });

    const htmlPath = path.join(__dirname, '../../renderer/index.html');
    this.kioskWindow.loadFile(htmlPath);

    this.kioskWindow.webContents.once('did-finish-load', () => {
      this.kioskWindow?.webContents.send('overlay:update', content);
    });
  }

  hideKioskOverlay(): void {
    this.relaxShortcuts();
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.hide();
      this.kioskWindow.destroy();
    }
    this.kioskWindow = null;
    // A session is now active: show the HUD over the game.
    this.sessionActive = true;
    this.showHud();
  }

  showHud(): void {
    this.hardenShortcuts();
    if (this.hudWindow && !this.hudWindow.isDestroyed()) {
      this.hudWindow.show();
      return;
    }
    const preloadPath = path.join(__dirname, '../../renderer/preload.js');
    this.hudWindow = new BrowserWindow({
      fullscreen: true,
      transparent: true,
      frame: false,
      alwaysOnTop: true,
      closable: false,
      skipTaskbar: true,
      focusable: false,
      webPreferences: {
        devTools: false,
        contextIsolation: true,
        sandbox: true,
        nodeIntegration: false,
        preload: preloadPath,
      },
    });
    // Click-through: mouse events pass to the game, forwarded by Electron.
    this.hudWindow.setIgnoreMouseEvents(true, { forward: true });
    this.hudWindow.on('closed', () => {
      this.hudWindow = null;
    });
    const htmlPath = path.join(__dirname, '../../renderer/hud.html');
    this.hudWindow.loadFile(htmlPath);
  }

  hideHud(): void {
    this.relaxShortcuts();
    if (this.hudWindow && !this.hudWindow.isDestroyed()) {
      this.hudWindow.hide();
      this.hudWindow.destroy();
    }
    this.hudWindow = null;
  }

  showLowTimeWarning(minutes: number): void {
    const win = this.sessionActive ? this.hudWindow : this.kioskWindow;
    if (win && !win.isDestroyed()) {
      win.webContents.send('overlay:low-time', { minutes });
    }
  }

  isKioskVisible(): boolean {
    return Boolean(
      this.kioskWindow &&
        !this.kioskWindow.isDestroyed() &&
        this.kioskWindow.isVisible(),
    );
  }

  updateTimer(timer: { elapsedSeconds: number }): void {
    const win = this.sessionActive ? this.hudWindow : this.kioskWindow;
    if (win && !win.isDestroyed()) {
      win.webContents.send('overlay:timer', { elapsedSeconds: timer.elapsedSeconds });
    }
  }

  sendAnnouncement(text: string, durationMs: number): void {
    const win = this.sessionActive ? this.hudWindow : this.kioskWindow;
    if (win && !win.isDestroyed()) {
      win.webContents.send('overlay:announcement', { text, durationMs });
    }
  }

  async restartPC(): Promise<void> {
    await execAsync('osascript -e \'tell application "System Events" to restart\'');
  }

  async shutdownPC(): Promise<void> {
    await execAsync('osascript -e \'tell application "System Events" to shut down\'');
  }

  async captureScreenshot(): Promise<Buffer> {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 1280, height: 720 },
    });

    if (!sources || sources.length === 0 || !sources[0].thumbnail) {
      console.warn(
        '[macOS] Screenshot failed: no screen sources — Screen Recording permission likely not granted (TCC).',
      );
      throw new Error('Screenshot capture unavailable: Screen Recording permission not granted');
    }

    const primaryScreen = sources[0];
    const pngBuffer = primaryScreen.thumbnail.toPNG();

    try {
      const compressed = await sharp(pngBuffer)
        .resize(1280, 720, { fit: 'inside', withoutEnlargement: true })
        .jpeg({ quality: 80 })
        .toBuffer();
      return compressed;
    } catch {
      return pngBuffer;
    }
  }

  async enableAutoStart(): Promise<void> {
    const plistPath = path.join(LAUNCH_AGENT_DIR, `${LAUNCH_AGENT_LABEL}.plist`);
    await fsp.writeFile(plistPath, this.buildLaunchAgentPlist(process.execPath), 'utf8');
  }

  async disableAutoStart(): Promise<void> {
    const plistPath = path.join(LAUNCH_AGENT_DIR, `${LAUNCH_AGENT_LABEL}.plist`);
    try {
      await fsp.unlink(plistPath);
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
        throw err;
      }
    }
  }

  async getSystemInfo(): Promise<SystemInfo> {
    const [cpu, mem, disk] = await Promise.all([
      si.cpu(),
      si.mem(),
      si.diskLayout(),
    ]);

    const totalDisk = disk.reduce((acc, d) => acc + (d.size || 0), 0);

    return {
      cpuModel: cpu.brand,
      cpuCores: cpu.cores || os.cpus().length,
      totalMemoryGB: Math.floor(mem.total / 1024 / 1024 / 1024),
      totalDiskGB: Math.floor(totalDisk / 1024 / 1024 / 1024),
      osName: process.platform,
      osVersion: os.release(),
      hostname: os.hostname(),
    };
  }

  private buildLaunchAgentPlist(execPath: string): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LAUNCH_AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>${execPath}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
  </dict>
</plist>
`;
  }

  private hardenShortcuts(): void {
    globalShortcut.registerAll(GLOBAL_SHORTCUTS, () => {});
  }

  private relaxShortcuts(): void {
    globalShortcut.unregisterAll();
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd agent && npx vitest run tests/platform/macos.test.ts`
Expected: PASS (all 15 tests green).

- [ ] **Step 5: Commit**

```bash
git add agent/src/main/platform/macos.ts agent/tests/platform/macos.test.ts
git commit -m "feat(7.1): implement MacosPlatformService (14-method IPlatformService mirror)"
```

---

### Task 2: Wire the factory + extend the factory test

**Files:**
- Modify: `agent/src/main/platform/index.ts`
- Modify: `agent/tests/platform/factory.test.ts`

**Interfaces:**
- Consumes: `MacosPlatformService` from `./macos.js` (created in Task 1).
- Produces: `getPlatformService()` now returns a `MacosPlatformService` on `darwin`.

- [ ] **Step 1: Add the failing factory test** (extend `agent/tests/platform/factory.test.ts`)

In the existing `vi.mock('electron', ...)` block, add `Menu` and `globalShortcut` so the macOS module can be imported and constructed:

```ts
vi.mock('electron', () => ({
  BrowserWindow: vi.fn().mockImplementation(() => ({
    webContents: { on: vi.fn(), send: vi.fn(), loadURL: vi.fn() },
    show: vi.fn(),
    hide: vi.fn(),
    destroy: vi.fn(),
    isDestroyed: vi.fn().mockReturnValue(false),
  })),
  desktopCapturer: {
    getSources: vi.fn().mockResolvedValue([
      { id: 'screen:0:0', name: 'Screen 1', thumbnail: { toPNG: vi.fn().mockReturnValue(Buffer.from('fake-png')) } },
    ]),
  },
  // Added for the darwin branch:
  Menu: { setApplicationMenu: vi.fn() },
  globalShortcut: { registerAll: vi.fn(), unregisterAll: vi.fn() },
}));
```

Add this test inside the existing `describe('getPlatformService', ...)` block (after the `win32` test):

```ts
  it('returns a service on darwin', async () => {
    Object.defineProperty(process, 'platform', { value: 'darwin' });

    const service = await getPlatformService();
    expect(service).toBeDefined();
    expect(service.constructor.name).toBe('MacosPlatformService');
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd agent && npx vitest run tests/platform/factory.test.ts`
Expected: FAIL on the new `darwin` test — `getPlatformService()` throws `Platform "darwin" is not yet supported`.

- [ ] **Step 3: Add the `darwin` branch to the factory** (`agent/src/main/platform/index.ts`)

Update the top-of-file comment and add the branch:

```ts
/**
 * Map of platform names to their implementation module paths.
 *
 * `win32` and `darwin` are implemented. `linux` is planned for Phase 7.
 */
const PLATFORM_MODULES: Record<string, string> = {
  win32: './windows.js',
  darwin: './macos.js',
  linux: './linux.js',
};
```

```ts
  if (platform === 'win32') {
    const { WindowsPlatformService } = await import('./windows.js');
    return new WindowsPlatformService();
  }

  if (platform === 'darwin') {
    const { MacosPlatformService } = await import('./macos.js');
    return new MacosPlatformService();
  }

  // Fallback guard — should be unreachable due to PLATFORM_MODULES check above.
  throw new Error(`Platform "${platform}" is not yet supported.`);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd agent && npx vitest run tests/platform/factory.test.ts`
Expected: PASS — `win32`, `darwin`, and the unsupported-platform tests all green.

- [ ] **Step 5: Commit**

```bash
git add agent/src/main/platform/index.ts agent/tests/platform/factory.test.ts
git commit -m "feat(7.1): wire MacosPlatformService into the platform factory"
```

---

### Task 3: Typecheck, lint, full test run, manual QA

**Files:**
- None new. Verification + documentation only.

**Interfaces:**
- Consumes: the implementation from Tasks 1–2.

- [ ] **Step 1: Typecheck the main process**

Run: `cd agent && npx tsc -p tsconfig.main.json --noEmit`
Expected: no type errors. (`macos.ts` must satisfy `IPlatformService`.)

- [ ] **Step 2: Lint**

Run: `cd agent && npm run lint`
Expected: no ESLint errors in `src`.

- [ ] **Step 3: Run the full agent test suite**

Run: `cd agent && npx vitest run`
Expected: all tests pass, including `macos.test.ts` and the extended `factory.test.ts`.

- [ ] **Step 4: Manual verification on a real Mac (cannot run in CI)**

Run each item on macOS and confirm:
1. Agent launches; the kiosk overlay shows full-screen and cannot be dismissed.
2. `Cmd+Q`, `Cmd+W`, `Cmd+H`, `Cmd+M` are no-ops while the overlay/HUD is visible (app does not quit/hide/minimize).
3. `Cmd+Tab` / `Cmd+Space` are blocked by kiosk mode.
4. Remote `RESTART` triggers an immediate macOS restart; remote `SHUTDOWN` triggers shutdown (no password prompt).
5. Remote screenshot succeeds **after** granting System Settings → Privacy & Security → Screen Recording for the agent; without the permission, the agent logs the TCC warning and reports a capture failure instead of crashing.
6. `enableAutoStart` writes `~/Library/LaunchAgents/com.arcade.agent.plist`; on next login the agent auto-launches. `disableAutoStart` removes it.
7. During an active session, the HUD overlays the running game with click-through (mouse reaches the game).

- [ ] **Step 5: Commit any fixes**

If Steps 1–3 surfaced issues, fix and commit:
```bash
git add -A
git commit -m "fix(7.1): address typecheck/lint/test findings for macOS platform"
```
If no fixes were needed, no commit is required.

---

## Self-Review (against the spec)

**1. Spec coverage** — every spec requirement maps to a task:
- Full 14-method interface → Task 1 (method-existence test + full class).
- Kiosk/HUD windows verbatim → Task 1 (`showKioskOverlay`/`hideKioskOverlay`/`showHud`/`hideHud` + IPC helpers).
- Hybrid shortcut hardening (`Menu.setApplicationMenu(null)` + `globalShortcut` + `before-input-event`) → Task 1 (constructor + `hardenShortcuts`/`relaxShortcuts` + `BLOCKED_SHORTCUTS`; tests assert register/unregister + preventDefault).
- `osascript` restart/shutdown (no sudo) → Task 1 (`restartPC`/`shutdownPC`; tests assert the osascript strings).
- TCC-aware screenshot → Task 1 (`captureScreenshot`; test asserts the no-source throw).
- LaunchAgent plist → Task 1 (`enableAutoStart`/`disableAutoStart` + `buildLaunchAgentPlist`; tests assert path, Label, `ProcessArguments=process.execPath`, `RunAtLoad`, `ProcessType Interactive`, ENOENT swallow).
- `getSystemInfo` via systeminformation → Task 1 (test asserts shape).
- Factory `darwin` branch → Task 2.

**2. Placeholder scan** — no TBD/TODO/"similar to" left; every step has concrete code or commands.

**3. Type consistency** — `MacosPlatformService` (named export, used by factory test and `index.ts`), `GLOBAL_SHORTCUTS`/`BLOCKED_SHORTCUTS` constants, `buildLaunchAgentPlist(execPath: string): string`, `LAUNCH_AGENT_LABEL = 'com.arcade.agent'` are consistent across the implementation and tests. `OverlayContent`/`SystemInfo`/`IPlatformService` come from `./types.js` (unchanged). The factory dynamic-imports `./macos.js` (matches the `./windows.js` pattern).

**Open defaults from the spec, preserved here:** `osName` returns `process.platform` (`'darwin'`) for parity with Windows; plist `Label` is `com.arcade.agent` (independent of the `appId` `com.neurotech.arcade.agent`).
