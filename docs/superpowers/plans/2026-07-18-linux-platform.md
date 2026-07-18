# Epic 7.2: Linux Platform Implementation (`linux.ts`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `agent/src/main/platform/linux.ts` so the Arcade agent runs natively on Linux — a full 14-method `IPlatformService` mirror of `windows.ts` plus Linux-specific OS calls (systemctl power control, XDG autostart `.desktop`, `desktopCapturer` screenshots) — and wire it into the platform factory.

**Architecture:** One new file `linux.ts` exporting `LinuxPlatformService implements IPlatformService`, mirroring `windows.ts` for the 8 window/info methods and using Linux-native calls for the 6 OS-specific ones. A module-level `isWayland()` gates a console warning + best-effort overlay flags on Wayland (the `setAlwaysOnTop('screen-saver')` flag is implemented per the Epic 7.2 task but is *not* a security control on Wayland — documented, not silently trusted). The factory `getPlatformService()` gains a `linux` branch.

**Tech Stack:** TypeScript / Electron (agent); vitest (agent tests).

## Global Constraints

- Implement **all 14** `IPlatformService` methods in `linux.ts` (interface compliance — TS fails otherwise). The 6 Epic 7.2 bullets are the Linux-specific ones; the other 8 mirror `windows.ts`.
- **X11 is the recommended client-PC session** (R-02); Wayland requires a dedicated kiosk compositor (Cage / gnome-kiosk / ubuntu-frame) for true lockdown.
- Wayland kiosk fallback = `setKiosk(true)` + `maximize()` + `setAlwaysOnTop(true, 'screen-saver')` **plus** `console.warn`, exactly as the Epic 7.2 task specifies.
- Power control: `systemctl reboot` / `systemctl poweroff` (literal task), with `loginctl reboot` / `loginctl poweroff` fallback on rejection.
- Screenshot: `desktopCapturer.getSources({types:['screen']})` → `sharp` resize 1280×720 JPEG 80%; **throw a clear, catchable `Error` when no sources are returned** ("graceful" = upstream `TAKE_SCREENSHOT` already reports capture failures).
- Auto-start: write `~/.config/autostart/arcade-agent.desktop` (XDG); delete on disable with `force: true` (idempotent).
- Leave the `darwin` factory branch throwing (its `macos.ts` is not present in this tree).
- Tests mirror `windows.test.ts` mocking; autostart mocks `node:fs` `promises` (not `child_process` `exec`).

---

## File Structure

- **Create:** `agent/src/main/platform/linux.ts` — `LinuxPlatformService` (14 methods) + exported `isWayland()`.
- **Modify:** `agent/src/main/platform/index.ts` — add the `linux` branch to `getPlatformService()`.
- **Create:** `agent/tests/platform/linux.test.ts` — mirrors `windows.test.ts` mocking; covers all 14 methods + `isWayland()` + Wayland warning.
- **Modify:** `agent/tests/platform/factory.test.ts` — add a `linux` case (overrides `process.platform`, cross-platform).
- **Modify:** `docs/agent-setup.md` — expand the `### Linux` subsection (X11 recommended, Wayland/Cage recipe, `.desktop` path, screenshot note).
- **Modify:** `docs/TODO.md` — tick the Epic 7.2 boxes.

---

### Task 1: Write the failing tests for `linux.ts`

**Files:**
- Create: `agent/tests/platform/linux.test.ts`

**Interfaces:**
- Consumes: `LinuxPlatformService`, `isWayland` (both created in Task 2).
- Produces: the test contract that Task 2 must satisfy.

- [ ] **Step 1: Write the test file**

Create `agent/tests/platform/linux.test.ts` with the full content below. It mirrors the `windows.test.ts` mocking pattern (mock `electron` with a `MockBrowserWindow` + `desktopCapturer`, mock `child_process`, `sharp`, `systeminformation`) and adds a `node:fs` `promises` mock for the autostart methods. `isWayland` is exported so it can be unit-tested directly.

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mockWebContents = {
  on: vi.fn(),
  once: vi.fn(),
  send: vi.fn(),
  loadURL: vi.fn(),
};

vi.mock('electron', async () => {
  const actual = await vi.importActual<object>('electron');

  class MockBrowserWindow {
    webContents = mockWebContents;
    show = vi.fn();
    hide = vi.fn();
    destroy = vi.fn();
    loadFile = vi.fn();
    maximize = vi.fn();
    setKiosk = vi.fn();
    setAlwaysOnTop = vi.fn();
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
          thumbnail: {
            toPNG: vi.fn().mockReturnValue(Buffer.from('fake-png')),
          },
        },
      ]),
    },
  };
});

// exec is used via promisify, so the mock must call its callback.
vi.mock('child_process', () => ({
  exec: vi.fn().mockImplementation((_, optionsOrCallback, maybeCallback) => {
    const callback =
      typeof optionsOrCallback === 'function'
        ? optionsOrCallback
        : maybeCallback;
    if (callback) {
      callback(null, 'stdout', 'stderr');
    }
    return undefined;
  }),
}));

vi.mock('sharp', () => {
  return {
    default: vi.fn().mockReturnValue({
      resize: vi.fn().mockReturnThis(),
      jpeg: vi.fn().mockReturnThis(),
      toBuffer: vi.fn().mockResolvedValue(Buffer.from('compressed-jpg')),
    }),
  };
});

vi.mock('systeminformation', () => ({
  default: {
    cpu: vi.fn().mockResolvedValue({ brand: 'Intel i7', cores: 8 }),
    mem: vi.fn().mockResolvedValue({ total: 34359738368 }),
    diskLayout: vi.fn().mockResolvedValue([{ size: 1000000000000 }]),
  },
}));

const mockFs = {
  mkdir: vi.fn().mockResolvedValue(undefined),
  writeFile: vi.fn().mockResolvedValue(undefined),
  rm: vi.fn().mockResolvedValue(undefined),
};

vi.mock('node:fs', () => ({
  promises: mockFs,
}));

import { LinuxPlatformService, isWayland } from '../../src/main/platform/linux.js';
import { exec } from 'child_process';
import { desktopCapturer } from 'electron';

describe('LinuxPlatformService', () => {
  let service: LinuxPlatformService;
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    service = new LinuxPlatformService();
    vi.clearAllMocks();
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    delete process.env.XDG_SESSION_TYPE;
    delete process.env.WAYLAND_DISPLAY;
  });

  afterEach(() => {
    service.hideKioskOverlay();
    warnSpy.mockRestore();
  });

  it('exposes all 14 IPlatformService methods', () => {
    const expected = [
      'showKioskOverlay',
      'hideKioskOverlay',
      'showHud',
      'hideHud',
      'showLowTimeWarning',
      'isKioskVisible',
      'updateTimer',
      'sendAnnouncement',
      'restartPC',
      'shutdownPC',
      'captureScreenshot',
      'enableAutoStart',
      'disableAutoStart',
      'getSystemInfo',
    ];
    for (const m of expected) {
      expect(typeof (service as Record<string, unknown>)[m]).toBe('function');
    }
  });

  it('calls systemctl reboot on restartPC', async () => {
    await service.restartPC();
    expect(exec).toHaveBeenCalledWith('systemctl reboot', expect.any(Function));
  });

  it('calls systemctl poweroff on shutdownPC', async () => {
    await service.shutdownPC();
    expect(exec).toHaveBeenCalledWith('systemctl poweroff', expect.any(Function));
  });

  it('returns a Buffer from captureScreenshot', async () => {
    const result = await service.captureScreenshot();
    expect(Buffer.isBuffer(result)).toBe(true);
  });

  it('throws when no screen sources are available (Wayland/PipeWire)', async () => {
    vi.mocked(desktopCapturer.getSources).mockResolvedValueOnce([]);
    await expect(service.captureScreenshot()).rejects.toThrow(/Screenshot unavailable/);
  });

  it('writes the XDG autostart .desktop file on enableAutoStart', async () => {
    await service.enableAutoStart();
    expect(mockFs.mkdir).toHaveBeenCalledWith(
      expect.stringContaining('autostart'),
      { recursive: true },
    );
    expect(mockFs.writeFile).toHaveBeenCalledWith(
      expect.stringContaining('arcade-agent.desktop'),
      expect.stringContaining('[Desktop Entry]'),
      { mode: 0o644 },
    );
  });

  it('removes the .desktop file on disableAutoStart', async () => {
    await service.disableAutoStart();
    expect(mockFs.rm).toHaveBeenCalledWith(
      expect.stringContaining('arcade-agent.desktop'),
      { force: true },
    );
  });

  it('getSystemInfo returns the expected shape', async () => {
    const info = await service.getSystemInfo();
    expect(info).toHaveProperty('cpuModel');
    expect(info).toHaveProperty('cpuCores');
    expect(info).toHaveProperty('totalMemoryGB');
    expect(info).toHaveProperty('totalDiskGB');
    expect(info).toHaveProperty('osName');
    expect(info).toHaveProperty('osVersion');
    expect(info).toHaveProperty('hostname');
  });

  it('isWayland true under XDG_SESSION_TYPE=wayland', () => {
    process.env.XDG_SESSION_TYPE = 'wayland';
    expect(isWayland()).toBe(true);
  });

  it('isWayland true when WAYLAND_DISPLAY is set', () => {
    process.env.WAYLAND_DISPLAY = 'wayland-0';
    expect(isWayland()).toBe(true);
  });

  it('isWayland false on X11', () => {
    delete process.env.XDG_SESSION_TYPE;
    delete process.env.WAYLAND_DISPLAY;
    expect(isWayland()).toBe(false);
  });

  it('warns (Wayland branch) when the kiosk is shown under Wayland', () => {
    process.env.XDG_SESSION_TYPE = 'wayland';
    service.showKioskOverlay({
      cafeName: 'Arcade',
      announcements: [],
      callStaffEnabled: true,
      sessionActive: false,
    });
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Wayland detected'),
    );
  });
});
```

- [ ] **Step 2: Run the tests to confirm they fail (module not found)**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx vitest run tests/platform/linux.test.ts`
Expected: FAIL — `Cannot find module '../../src/main/platform/linux.js'` (the implementation does not exist yet).

- [ ] **Step 3: Commit the test (red)**

```bash
git add agent/tests/platform/linux.test.ts
git commit -m "test(linux): add failing tests for LinuxPlatformService"
```

---

### Task 2: Implement `linux.ts`

**Files:**
- Create: `agent/src/main/platform/linux.ts`

**Interfaces:**
- Consumes: `IPlatformService`, `OverlayContent`, `SystemInfo` from `./types.js`; `electron` (`BrowserWindow`, `desktopCapturer`); `child_process` (`exec`); `sharp`; `systeminformation`; `node:fs/promises`; `node:os`.
- Produces: `LinuxPlatformService` (14 methods) + exported `isWayland()` — imported by `index.ts` (Task 3) and `linux.test.ts` (Task 1).

- [ ] **Step 1: Write `linux.ts`**

Create `agent/src/main/platform/linux.ts` with this complete content. It mirrors `windows.ts` for the window/info methods and adds Linux-specific OS calls. Note `isWayland` is exported so the test can call it directly.

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

const AUTO_START_DIR = path.join(os.homedir(), '.config', 'autostart');
const AUTO_START_FILE = path.join(AUTO_START_DIR, 'arcade-agent.desktop');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BLOCKED_SHORTCUTS = [
  'Alt+F4',
  'Alt+Shift+I',
  'Control+Shift+I',
  'Control+P',
  'F12',
  'F11',
  'Escape',
];

/** True when running under a native Wayland session. */
export function isWayland(): boolean {
  return (
    process.env.XDG_SESSION_TYPE === 'wayland' ||
    Boolean(process.env.WAYLAND_DISPLAY)
  );
}

export class LinuxPlatformService implements IPlatformService {
  private kioskWindow: BrowserWindow | null = null;
  private hudWindow: BrowserWindow | null = null;
  private sessionActive = false;

  showKioskOverlay(content: OverlayContent): void {
    this.sessionActive = false;
    this.hideHud();
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.show();
      this.kioskWindow.webContents.send('overlay:update', content);
      return;
    }

    const preloadPath = path.join(__dirname, '../../renderer/preload.js');

    const win = new BrowserWindow({
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

    if (isWayland()) {
      win.setKiosk(true);
      win.maximize();
      win.setAlwaysOnTop(true, 'screen-saver');
      console.warn(
        '[linux] Wayland detected: kiosk overlay is NOT bypass-proof. ' +
          'Deploy under a Wayland kiosk compositor (Cage / gnome-kiosk / ubuntu-frame) ' +
          'for true lockdown. See docs/agent-setup.md.',
      );
    }

    win.webContents.on('context-menu', (event) => {
      event.preventDefault();
    });

    win.webContents.on('before-input-event', (event, input) => {
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

    win.on('closed', () => {
      this.kioskWindow = null;
    });

    const htmlPath = path.join(__dirname, '../../renderer/index.html');
    win.loadFile(htmlPath);

    this.kioskWindow = win;

    win.webContents.once('did-finish-load', () => {
      this.kioskWindow?.webContents.send('overlay:update', content);
    });
  }

  hideKioskOverlay(): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.hide();
      this.kioskWindow.destroy();
    }
    this.kioskWindow = null;
    this.sessionActive = true;
    this.showHud();
  }

  showHud(): void {
    if (this.hudWindow && !this.hudWindow.isDestroyed()) {
      this.hudWindow.show();
      return;
    }
    const preloadPath = path.join(__dirname, '../../renderer/preload.js');
    const win = new BrowserWindow({
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
    win.setIgnoreMouseEvents(true, { forward: true });
    win.on('closed', () => {
      this.hudWindow = null;
    });
    const htmlPath = path.join(__dirname, '../../renderer/hud.html');
    win.loadFile(htmlPath);
    this.hudWindow = win;
  }

  hideHud(): void {
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
      win.webContents.send('overlay:timer', {
        elapsedSeconds: timer.elapsedSeconds,
      });
    }
  }

  sendAnnouncement(text: string, durationMs: number): void {
    const win = this.sessionActive ? this.hudWindow : this.kioskWindow;
    if (win && !win.isDestroyed()) {
      win.webContents.send('overlay:announcement', { text, durationMs });
    }
  }

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

  async captureScreenshot(): Promise<Buffer> {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 1280, height: 720 },
    });

    if (!sources || sources.length === 0) {
      throw new Error(
        'Screenshot unavailable on this session (no screen sources; Wayland/PipeWire ' +
          'portal not permitted or X11 display absent).',
      );
    }

    const primaryScreen = sources[0];
    let pngBuffer: Buffer;

    if (primaryScreen.thumbnail) {
      pngBuffer = primaryScreen.thumbnail.toPNG();
    } else {
      throw new Error('Screenshot thumbnail not available');
    }

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
}
```

- [ ] **Step 2: Run the new tests**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx vitest run tests/platform/linux.test.ts`
Expected: all PASS (13 cases).

- [ ] **Step 3: Type-check the agent main process**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx tsc --noEmit -p tsconfig.main.json`
Expected: no errors (the `linux.ts` file satisfies `IPlatformService`).

- [ ] **Step 4: Commit**

```bash
git add agent/src/main/platform/linux.ts
git commit -m "feat(agent): implement LinuxPlatformService (Epic 7.2)"
```

---

### Task 3: Wire the `linux` branch into the factory

**Files:**
- Modify: `agent/src/main/platform/index.ts:33-39` (`getPlatformService` win32 branch + fallback)
- Modify: `agent/tests/platform/factory.test.ts:75` (add linux case)

**Interfaces:**
- Consumes: `LinuxPlatformService` from `./linux.js` (Task 2).
- Produces: `getPlatformService()` now returns a `LinuxPlatformService` when `process.platform === 'linux'`.

- [ ] **Step 1: Add the `linux` branch to `index.ts`**

In `agent/src/main/platform/index.ts`, insert a `linux` branch after the existing `win32` branch (before the fallback `throw`):

Replace:
```ts
  if (platform === 'win32') {
    const { WindowsPlatformService } = await import('./windows.js');
    return new WindowsPlatformService();
  }

  // Fallback guard — should be unreachable due to PLATFORM_MODULES check above.
  throw new Error(`Platform "${platform}" is not yet supported.`);
```

with:
```ts
  if (platform === 'win32') {
    const { WindowsPlatformService } = await import('./windows.js');
    return new WindowsPlatformService();
  }

  if (platform === 'linux') {
    const { LinuxPlatformService } = await import('./linux.js');
    return new LinuxPlatformService();
  }

  // Fallback guard — should be unreachable due to PLATFORM_MODULES check above.
  throw new Error(`Platform "${platform}" is not yet supported.`);
```

- [ ] **Step 2: Add a `linux` case to `factory.test.ts`**

Append this test inside the `describe('getPlatformService', ...)` block in `agent/tests/platform/factory.test.ts` (after the `win32` test):

```ts
  it('returns a LinuxPlatformService on linux', async () => {
    Object.defineProperty(process, 'platform', { value: 'linux' });

    const service = await getPlatformService();
    expect(service).toBeDefined();
    expect(service.constructor.name).toBe('LinuxPlatformService');
  });
```

- [ ] **Step 3: Run the factory tests**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx vitest run tests/platform/factory.test.ts`
Expected: all PASS (the new `linux` case plus the pre-existing `win32` + unsupported cases).

- [ ] **Step 4: Type-check**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx tsc --noEmit -p tsconfig.main.json`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add agent/src/main/platform/index.ts agent/tests/platform/factory.test.ts
git commit -m "feat(agent): wire linux branch into getPlatformService factory"
```

---

### Task 4: Document the Linux setup in `docs/agent-setup.md`

**Files:**
- Modify: `docs/agent-setup.md:236-239` (the `### Linux` stub)

**Interfaces:**
- Consumes: the implemented behaviour (XDG autostart path, Wayland/Cage note, screenshot caveat).
- Produces: accurate operator-facing Linux docs.

- [ ] **Step 1: Expand the `### Linux` subsection**

Replace the stub (currently):
```markdown
### Linux

- systemd service or `.desktop` file in `~/.config/autostart/`
- Enable via Dashboard or `platform.enableAutoStart()`.
```

with:
```markdown
### Linux

- **Recommended session:** **X11** for client (gaming) PCs. Kiosk lockdown is
  reliable on X11; see the Wayland note below.
- **Auto-start:** `~/.config/autostart/arcade-agent.desktop` (XDG autostart).
  Enable via Dashboard (**Settings → Agent → Auto-Start**) or
  `platform.enableAutoStart()`. The agent writes:
  ```
  [Desktop Entry]
  Type=Application
  Name=Arcade Agent
  Exec=<path to agent binary>
  X-GNOME-Autostart-enabled=true
  X-GNOME-Autostart-Delay=5
  ```
  Disable via Dashboard or `platform.disableAutoStart()` (deletes the file;
  safe to run even if it is already absent).
- **Power control:** `systemctl reboot` / `systemctl poweroff` (falls back to
  `loginctl reboot` / `loginctl poweroff`). The launching user needs polkit
  permission to power off / reboot the machine.
- **Wayland (not recommended for v1.0):** On a native Wayland session, no
  Electron app-level API can prevent the user from switching away — the
  compositor owns window stacking. The agent applies `setKiosk` + a
  `screen-saver` always-on-top hint and logs a warning, but the overlay is
  **not** bypass-proof on Wayland. For true lockdown, run the agent under a
  dedicated single-app Wayland compositor, e.g.:
  ```
  cage /opt/ArcadeAgent/arcade-agent --ozone-platform-hint=auto
  ```
  (`gnome-kiosk` and `ubuntu-frame` are alternatives.) This is the secure
  deployment path; X11 is the simpler one.
- **Screenshots:** Work natively on X11. On Wayland they go through the
  PipeWire portal and require a user-granted screen-share prompt; if denied or
  unavailable, the capture fails with a clear error (see Troubleshooting).
```

- [ ] **Step 2: Commit**

```bash
git add docs/agent-setup.md
git commit -m "docs(agent): expand Linux setup section (X11, autostart, Wayland)"
```

---

### Task 5: Full verification + tick the Epic 7.2 boxes

**Files:**
- Modify: `docs/TODO.md` (Epic 7.2 task boxes)

**Interfaces:**
- Consumes: the implemented + documented behaviour (Tasks 1-4).
- Produces: green test/lint/type-check state and accurate project tracking.

- [ ] **Step 1: Run the full agent test suite**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx vitest run`
Expected: all PASS (includes `linux.test.ts` and the updated `factory.test.ts`).

- [ ] **Step 2: Lint the agent**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npm run lint`
Expected: clean (no errors).

- [ ] **Step 3: Type-check both agent configs**

Run: `cd "E:/Ongoing Projects/Arcade/agent" && npx tsc --noEmit -p tsconfig.main.json && npx tsc --noEmit -p tsconfig.renderer.json`
Expected: no errors.

- [ ] **Step 4: Tick the Epic 7.2 boxes in `docs/TODO.md`**

In `docs/TODO.md`, change the Epic 7.2 `Task: Implement linux.ts` block so the
task and its sub-bullets are marked complete:

```markdown
- [x] **Task: Implement `linux.ts`**
  - [x] `showKioskOverlay()` / `hideKioskOverlay()`: `win.setKiosk(true/false)`; on Wayland, add fallback: maximise + `setAlwaysOnTop(true, 'screen-saver')` (FR-AGENT-002b)
  - [x] `restartPC()`: `exec('systemctl reboot')`
  - [x] `shutdownPC()`: `exec('systemctl poweroff')`
  - [x] `captureScreenshot()`: `desktopCapturer` (X11 works natively; Wayland requires workaround — handle gracefully if unavailable)
  - [x] `enableAutoStart()`: write `~/.config/autostart/arcade-agent.desktop`
  - [x] `disableAutoStart()`: delete the `.desktop` file
```

- [ ] **Step 5: Commit**

```bash
git add docs/TODO.md
git commit -m "docs(7.2): mark Linux platform implementation complete"
```

---

## Self-Review Notes (per skill checklist)

- **Spec coverage:** §1 scaffold/isWayland → Task 2 (`isWayland` exported); §2 kiosk + Wayland warning → Task 2 `showKioskOverlay` + `console.warn`; §3 power (systemctl + loginctl) → Task 2 `restartPC`/`shutdownPC`; §4 screenshot + empty-source throw → Task 2 `captureScreenshot` + linux.test "throws when no sources"; §5 autostart `.desktop` → Task 2 `enableAutoStart`/`disableAutoStart` + test; §6 HUD/timer/announcement/lowtime/visibility/systeminfo mirror → Task 2 full class; §7 factory → Task 3; §8 tests → Task 1 + Task 3 factory case; §9 docs → Task 4 + Task 5 TODO tick. All mapped.
- **Placeholder scan:** no TBD/TODO/"implement later"; every code step shows the actual code (full `linux.ts`, full test file, exact `index.ts` diff, exact doc replacement).
- **Type consistency:** `isWayland(): boolean` is the single exported name used by both `linux.ts` (internal + test) and `linux.test.ts`; `captureScreenshot(): Promise<Buffer>` matches `IPlatformService`; `enableAutoStart`/`disableAutoStart` write/delete `AUTO_START_FILE` (same constant in impl and asserted by path in test); `updateTimer({ elapsedSeconds: number })` matches `types.ts`.
- **One deviation from the spec, approved:** the `loginctl` fallback in power control (spec Decision table, "Approved as included") — implemented in Task 2.
- **Two things deliberately out of scope (sibling TODO tasks):** the `docs/autostart/` systemd `.service` template (line 1447) and the `electron-builder.yml` Linux targets (lines 1444-1446). Runtime XDG autostart is covered here.
