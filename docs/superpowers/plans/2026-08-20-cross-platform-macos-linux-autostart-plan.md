# Cross-Platform Deferred Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Section M cross-platform deferred items (M.1–M.6): macOS platform service fixes, Linux Wayland verification tests, auto-start production unit files, and hardware verification checklists.

**Architecture:** Three independent workstreams (macOS, Linux Wayland, Auto-Start) with shared test infrastructure. All CI tests run on Windows via mocks; hardware verification deferred to checklists.

**Tech Stack:** TypeScript (agent), Vitest, Electron, Node.js child_process, systemd, LaunchAgent, Windows Registry

## Global Constraints

- All CI tests must pass on Windows (no macOS/Linux runners)
- Follow existing test patterns: mirror `agent/tests/platform/windows.test.ts` and `linux.test.ts`
- Mock Electron, `child_process`, `sharp`, `systeminformation`, `node:fs/promises`
- No TBD/TODO placeholders — every step has complete code
- Frequent commits after each task
- DRY, YAGNI, TDD

---

## Task 1: Fix macOS BLOCKED_SHORTCUTS

**Files:**
- Modify: `agent/src/main/platform/macos.ts:25-33`
- Test: `agent/tests/platform/macos.test.ts` (new)

**Interfaces:**
- Consumes: `BLOCKED_SHORTCUTS` constant used in `before-input-event` handler
- Produces: Updated shortcut list for macOS (Meta+Q, Meta+W, Meta+H, Meta+M, etc.)

- [ ] **Step 1: Write failing test for macOS shortcuts**

```typescript
// agent/tests/platform/macos.test.ts
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
    setIgnoreMouseEvents = vi.fn();
    isDestroyed = vi.fn().mockReturnValue(false);
    isVisible = vi.fn().mockReturnValue(true);
    on = vi.fn();
    getBounds = vi.fn().mockReturnValue({ x: 0, y: 0, width: 1920, height: 1080 });
    constructor(_opts?: Record<string, unknown>) {}
  }
  const mockDesktopCapturer = {
    getSources: vi.fn().mockResolvedValue([{ id: 'screen:0:0', name: 'Screen 1', thumbnail: { toPNG: vi.fn().mockReturnValue(Buffer.from('fake-png')) } }]),
  };
  const mockScreen = { getCursorScreenPoint: vi.fn().mockReturnValue({ x: 0, y: 0 }) };
  const mockPowerMonitor = { on: vi.fn(), off: vi.fn() };
  return { ...actual, default: { BrowserWindow: MockBrowserWindow, desktopCapturer: mockDesktopCapturer, screen: mockScreen, powerMonitor: mockPowerMonitor }, BrowserWindow: MockBrowserWindow, desktopCapturer: mockDesktopCapturer, screen: mockScreen, powerMonitor: mockPowerMonitor };
});

vi.mock('child_process', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, exec: vi.fn().mockImplementation((_, optionsOrCallback, maybeCallback) => { const callback = typeof optionsOrCallback === 'function' ? optionsOrCallback : maybeCallback; if (callback) callback(null, 'stdout', 'stderr'); return undefined; }) };
});

vi.mock('sharp', () => ({ default: vi.fn().mockReturnValue({ resize: vi.fn().mockReturnThis(), jpeg: vi.fn().mockReturnThis(), toBuffer: vi.fn().mockResolvedValue(Buffer.from('compressed-jpg')) }) }));

vi.mock('systeminformation', () => ({ default: { cpu: vi.fn().mockResolvedValue({ brand: 'Apple M2', cores: 8 }), mem: vi.fn().mockResolvedValue({ total: 34359738368 }), diskLayout: vi.fn().mockResolvedValue([{ size: 1000000000000 }]) } }));

const mockFs = vi.hoisted(() => ({ mkdir: vi.fn().mockResolvedValue(undefined), writeFile: vi.fn().mockResolvedValue(undefined), rm: vi.fn().mockResolvedValue(undefined) }));
vi.mock('node:fs', () => ({ default: { promises: mockFs }, promises: mockFs }));

import { MacOSPlatformService } from '../../src/main/platform/macos.js';
import { screen } from 'electron';

describe('MacOSPlatformService - shortcuts', () => {
  let service: MacOSPlatformService;

  beforeEach(() => {
    service = new MacOSPlatformService();
    vi.clearAllMocks();
    service.showKioskOverlay({ cafeName: 'Test', announcements: [], callStaffEnabled: true, sessionActive: false });
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
  });

  it('blocks Cmd+Q (Meta+Q)', () => {
    const handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    expect(handler).toBeDefined();
    handler?.({ key: 'q', meta: true, control: false, alt: false, shift: false }, { preventDefault: vi.fn() });
    // Verify preventDefault was called - this will fail until shortcuts are updated
  });

  it('blocks Cmd+W (Meta+W)', () => {
    const handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    handler?.({ key: 'w', meta: true, control: false, alt: false, shift: false }, { preventDefault: vi.fn() });
  });

  it('blocks Cmd+H (Meta+H)', () => {
    const handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    handler?.({ key: 'h', meta: true, control: false, alt: false, shift: false }, { preventDefault: vi.fn() });
  });

  it('blocks Cmd+M (Meta+M)', () => {
    const handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    handler?.({ key: 'm', meta: true, control: false, alt: false, shift: false }, { preventDefault: vi.fn() });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agent && npx vitest run tests/platform/macos.test.ts -v
```
Expected: FAIL - shortcuts not blocked (current code uses Windows shortcuts)

- [ ] **Step 3: Fix BLOCKED_SHORTCUTS in macos.ts**

```typescript
// agent/src/main/platform/macos.ts:25-33
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

- [ ] **Step 4: Run test to verify it passes**

```bash
cd agent && npx vitest run tests/platform/macos.test.ts -v
```
Expected: PASS - all 4 macOS shortcuts blocked

- [ ] **Step 5: Commit**

```bash
git add agent/src/main/platform/macos.ts agent/tests/platform/macos.test.ts
git commit -m "fix(macos): update BLOCKED_SHORTCUTS for macOS (Cmd+Q/W/H/M)"
```

---

## Task 2: Fix macOS restartPC/shutdownPC to use osascript

**Files:**
- Modify: `agent/src/main/platform/macos.ts:267-275`
- Test: `agent/tests/platform/macos.test.ts` (extend)

**Interfaces:**
- Consumes: `execAsync` from `child_process`
- Produces: `osascript` commands for restart/shutdown

- [ ] **Step 1: Write failing test for osascript commands**

```typescript
// Add to agent/tests/platform/macos.test.ts
import { exec } from 'child_process';

describe('MacOSPlatformService - restart/shutdown', () => {
  let service: MacOSPlatformService;

  beforeEach(() => {
    service = new MacOSPlatformService();
    vi.clearAllMocks();
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
  });

  it('restartPC calls osascript for restart', async () => {
    await service.restartPC();
    expect(exec).toHaveBeenCalledWith("osascript -e 'tell app \"System Events\" to restart'", expect.any(Function));
  });

  it('shutdownPC calls osascript for shutdown', async () => {
    await service.shutdownPC();
    expect(exec).toHaveBeenCalledWith("osascript -e 'tell app \"System Events\" to shut down'", expect.any(Function));
  });

  it('does not execute commands in test mode', async () => {
    vi.doMock('./safety.js', () => ({ isTestMode: () => true }));
    await service.restartPC();
    await service.shutdownPC();
    expect(exec).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agent && npx vitest run tests/platform/macos.test.ts -v
```
Expected: FAIL - current code uses `sudo shutdown`

- [ ] **Step 3: Update restartPC/shutdownPC in macos.ts**

```typescript
// agent/src/main/platform/macos.ts:267-275
async restartPC(): Promise<void> {
  if (isTestMode()) return;
  await execAsync("osascript -e 'tell app \"System Events\" to restart'");
}

async shutdownPC(): Promise<void> {
  if (isTestMode()) return;
  await execAsync("osascript -e 'tell app \"System Events\" to shut down'");
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd agent && npx vitest run tests/platform/macos.test.ts -v
```
Expected: PASS - osascript commands called

- [ ] **Step 5: Commit**

```bash
git add agent/src/main/platform/macos.ts agent/tests/platform/macos.test.ts
git commit -m "fix(macos): use osascript for restartPC/shutdownPC"
```

---

## Task 3: Complete macos.test.ts with all IPlatformService methods

**Files:**
- Create: `agent/tests/platform/macos.test.ts` (complete)

**Interfaces:**
- Consumes: All mocks from Tasks 1-2
- Produces: Full test coverage for 15 IPlatformService methods

- [ ] **Step 1: Write complete test file mirroring windows.test.ts**

```typescript
// agent/tests/platform/macos.test.ts (complete)
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
    setIgnoreMouseEvents = vi.fn();
    isDestroyed = vi.fn().mockReturnValue(false);
    isVisible = vi.fn().mockReturnValue(true);
    on = vi.fn();
    getBounds = vi.fn().mockReturnValue({ x: 0, y: 0, width: 1920, height: 1080 });
    constructor(_opts?: Record<string, unknown>) {}
  }
  const mockDesktopCapturer = {
    getSources: vi.fn().mockResolvedValue([{ id: 'screen:0:0', name: 'Screen 1', thumbnail: { toPNG: vi.fn().mockReturnValue(Buffer.from('fake-png')) } }]),
  };
  const mockScreen = { getCursorScreenPoint: vi.fn().mockReturnValue({ x: 0, y: 0 }) };
  const mockPowerMonitor = { on: vi.fn(), off: vi.fn() };
  return { ...actual, default: { BrowserWindow: MockBrowserWindow, desktopCapturer: mockDesktopCapturer, screen: mockScreen, powerMonitor: mockPowerMonitor }, BrowserWindow: MockBrowserWindow, desktopCapturer: mockDesktopCapturer, screen: mockScreen, powerMonitor: mockPowerMonitor };
});

vi.mock('child_process', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, exec: vi.fn().mockImplementation((_, optionsOrCallback, maybeCallback) => { const callback = typeof optionsOrCallback === 'function' ? optionsOrCallback : maybeCallback; if (callback) callback(null, 'stdout', 'stderr'); return undefined; }) };
});

vi.mock('sharp', () => ({ default: vi.fn().mockReturnValue({ resize: vi.fn().mockReturnThis(), jpeg: vi.fn().mockReturnThis(), toBuffer: vi.fn().mockResolvedValue(Buffer.from('compressed-jpg')) }) }));

vi.mock('systeminformation', () => ({ default: { cpu: vi.fn().mockResolvedValue({ brand: 'Apple M2', cores: 8 }), mem: vi.fn().mockResolvedValue({ total: 34359738368 }), diskLayout: vi.fn().mockResolvedValue([{ size: 1000000000000 }]) } }));

const mockFs = vi.hoisted(() => ({ mkdir: vi.fn().mockResolvedValue(undefined), writeFile: vi.fn().mockResolvedValue(undefined), rm: vi.fn().mockResolvedValue(undefined) }));
vi.mock('node:fs', () => ({ default: { promises: mockFs }, promises: mockFs }));

import { MacOSPlatformService } from '../../src/main/platform/macos.js';
import { exec } from 'child_process';
import { desktopCapturer, screen, powerMonitor } from 'electron';

describe('MacOSPlatformService', () => {
  let service: MacOSPlatformService;
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    service = new MacOSPlatformService();
    vi.clearAllMocks();
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
    warnSpy.mockRestore();
  });

  it('exposes all 15 IPlatformService methods', () => {
    const expected = [
      'showKioskOverlay', 'hideKioskOverlay', 'setKioskClickThrough',
      'showLowTimeWarning', 'isKioskVisible', 'updateTimer',
      'sendAnnouncement', 'sendConfigToOverlay', 'sendToOverlayAndHud',
      'restartPC', 'shutdownPC', 'captureScreenshot',
      'enableAutoStart', 'disableAutoStart', 'getSystemInfo',
    ];
    for (const m of expected) {
      expect(typeof (service as Record<string, unknown>)[m]).toBe('function');
    }
  });

  it('never runs osascript restart under test mode', async () => {
    await service.restartPC();
    expect(exec).not.toHaveBeenCalled();
  });

  it('never runs osascript shutdown under test mode', async () => {
    await service.shutdownPC();
    expect(exec).not.toHaveBeenCalled();
  });

  it('returns a Buffer from captureScreenshot', async () => {
    const result = await service.captureScreenshot();
    expect(Buffer.isBuffer(result)).toBe(true);
  });

  it('throws when no screen sources are available', async () => {
    vi.mocked(desktopCapturer.getSources).mockResolvedValueOnce([]);
    await expect(service.captureScreenshot()).rejects.toThrow(/No screen sources available/);
  });

  it('never writes LaunchAgent plist under test mode', async () => {
    await service.enableAutoStart();
    expect(mockFs.mkdir).not.toHaveBeenCalled();
    expect(mockFs.writeFile).not.toHaveBeenCalled();
  });

  it('never removes LaunchAgent plist under test mode', async () => {
    await service.disableAutoStart();
    expect(mockFs.rm).not.toHaveBeenCalled();
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

  describe('hotspot cursor polling', () => {
    let send: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      vi.useFakeTimers();
      service = new MacOSPlatformService();
      vi.clearAllMocks();
      service.showKioskOverlay({ cafeName: 'Test', announcements: [], callStaffEnabled: true, sessionActive: false });
      const mockWindow = (service as any).kioskWindow;
      send = mockWindow.webContents.send;
      send.mockClear();
    });

    afterEach(() => { vi.useRealTimers(); });

    it('full mode: notifies hotspot when cursor enters bottom-right corner', () => {
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 100, y: 100 });
      vi.advanceTimersByTime(500);
      expect(send).not.toHaveBeenCalledWith('overlay:hotspot', true);
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1905, y: 1065 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', true);
    });

    it('full mode: notifies hotspot exit when cursor leaves corner', () => {
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1905, y: 1065 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', true);
      send.mockClear();
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 100, y: 100 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', false);
    });

    it('minimal mode: notifies hotspot along full right edge', () => {
      service.hideKioskOverlay();
      send.mockClear();
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1905, y: 500 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', true);
    });

    it('does not notify for cursor outside window', () => {
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1920, y: 100 });
      vi.advanceTimersByTime(500);
      expect(send).not.toHaveBeenCalledWith('overlay:hotspot', true);
    });
  });

  describe('power monitor events', () => {
    let send: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      service = new MacOSPlatformService();
      vi.clearAllMocks();
      service.showKioskOverlay({ cafeName: 'Test', announcements: [], callStaffEnabled: true, sessionActive: true });
      const mockWindow = (service as any).kioskWindow;
      send = mockWindow.webContents.send;
      send.mockClear();
    });

    it('registers suspend/resume/lock/unlock handlers on init', () => {
      expect(powerMonitor.on).toHaveBeenCalledWith('suspend', expect.any(Function));
      expect(powerMonitor.on).toHaveBeenCalledWith('resume', expect.any(Function));
      expect(powerMonitor.on).toHaveBeenCalledWith('lock-screen', expect.any(Function));
      expect(powerMonitor.on).toHaveBeenCalledWith('unlock-screen', expect.any(Function));
    });

    it('on suspend: sends overlay:suspend and marks suspended', () => {
      const suspendHandler = vi.mocked(powerMonitor.on).mock.calls.find((c) => c[0] === 'suspend')?.[1];
      expect(suspendHandler).toBeDefined();
      suspendHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:suspend');
    });

    it('on resume: restores full mode, clears suspended, sends overlay:resume and request-sync', () => {
      const resumeHandler = vi.mocked(powerMonitor.on).mock.calls.find((c) => c[0] === 'resume')?.[1];
      expect(resumeHandler).toBeDefined();
      resumeHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:set-minimal', false);
      expect(send).toHaveBeenCalledWith('overlay:resume');
      expect(send).toHaveBeenCalledWith('overlay:request-sync', undefined);
    });

    it('lock-screen triggers suspend behavior', () => {
      const lockHandler = vi.mocked(powerMonitor.on).mock.calls.find((c) => c[0] === 'lock-screen')?.[1];
      expect(lockHandler).toBeDefined();
      lockHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:suspend');
    });

    it('unlock-screen triggers resume behavior', () => {
      const unlockHandler = vi.mocked(powerMonitor.on).mock.calls.find((c) => c[0] === 'unlock-screen')?.[1];
      expect(unlockHandler).toBeDefined();
      unlockHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:set-minimal', false);
    });
  });

  // Shortcut tests from Task 1
  describe('shortcut blocking', () => {
    let handler: ((event: any, input: any) => void) | undefined;

    beforeEach(() => {
      service = new MacOSPlatformService();
      vi.clearAllMocks();
      service.showKioskOverlay({ cafeName: 'Test', announcements: [], callStaffEnabled: true, sessionActive: false });
      handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    });

    const preventDefault = vi.fn();
    const testShortcut = (key: string, meta = true, control = false, alt = false, shift = false) => {
      preventDefault.mockClear();
      handler?.({ key, meta, control, alt, shift }, { preventDefault });
      return preventDefault;
    };

    it('blocks Cmd+Q (Meta+Q)', () => { expect(testShortcut('q', true)).toHaveBeenCalled(); });
    it('blocks Cmd+W (Meta+W)', () => { expect(testShortcut('w', true)).toHaveBeenCalled(); });
    it('blocks Cmd+H (Meta+H)', () => { expect(testShortcut('h', true)).toHaveBeenCalled(); });
    it('blocks Cmd+M (Meta+M)', () => { expect(testShortcut('m', true)).toHaveBeenCalled(); });
    it('blocks Cmd+Shift+I', () => { expect(testShortcut('i', true, false, false, true)).toHaveBeenCalled(); });
    it('blocks Ctrl+Shift+I', () => { expect(testShortcut('i', false, true, false, true)).toHaveBeenCalled(); });
    it('blocks Ctrl+P', () => { expect(testShortcut('p', false, true)).toHaveBeenCalled(); });
    it('blocks F12', () => { expect(testShortcut('F12')).toHaveBeenCalled(); });
    it('blocks F11', () => { expect(testShortcut('F11')).toHaveBeenCalled(); });
    it('blocks Escape', () => { expect(testShortcut('Escape')).toHaveBeenCalled(); });
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd agent && npx vitest run tests/platform/macos.test.ts -v
```
Expected: PASS - all 25+ tests pass

- [ ] **Step 3: Commit**

```bash
git add agent/tests/platform/macos.test.ts
git commit -m "test(macos): complete MacOSPlatformService test coverage (25+ tests)"
```

---

## Task 4: Linux Wayland CI Smoke Tests

**Files:**
- Modify: `agent/tests/platform/linux.test.ts` (extend existing)

**Interfaces:**
- Consumes: Existing mocks in linux.test.ts
- Produces: Wayland detection, kiosk flags, screenshot fallback tests

- [ ] **Step 1: Write failing Wayland tests**

```typescript
// Add to agent/tests/platform/linux.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LinuxPlatformService, isWayland } from '../../src/main/platform/linux.js';
import { desktopCapturer, screen, powerMonitor } from 'electron';

describe('LinuxPlatformService - Wayland', () => {
  let service: LinuxPlatformService;

  beforeEach(() => {
    service = new LinuxPlatformService();
    vi.clearAllMocks();
    delete process.env.XDG_SESSION_TYPE;
    delete process.env.WAYLAND_DISPLAY;
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
  });

  describe('isWayland detection', () => {
    it('returns true when XDG_SESSION_TYPE=wayland', () => {
      process.env.XDG_SESSION_TYPE = 'wayland';
      expect(isWayland()).toBe(true);
    });

    it('returns true when WAYLAND_DISPLAY is set', () => {
      process.env.WAYLAND_DISPLAY = 'wayland-0';
      expect(isWayland()).toBe(true);
    });

    it('returns false on X11', () => {
      delete process.env.XDG_SESSION_TYPE;
      delete process.env.WAYLAND_DISPLAY;
      expect(isWayland()).toBe(false);
    });
  });

  describe('Wayland kiosk flags', () => {
    it('applies setKiosk, maximize, setAlwaysOnTop when isWayland()', () => {
      process.env.XDG_SESSION_TYPE = 'wayland';
      service.showKioskOverlay({
        cafeName: 'Test',
        announcements: [],
        callStaffEnabled: true,
        sessionActive: false,
      });
      const mockWindow = (service as any).kioskWindow;
      expect(mockWindow.setKiosk).toHaveBeenCalledWith(true);
      expect(mockWindow.maximize).toHaveBeenCalled();
      expect(mockWindow.setAlwaysOnTop).toHaveBeenCalledWith(true, 'screen-saver');
    });

    it('does NOT apply Wayland flags on X11', () => {
      delete process.env.XDG_SESSION_TYPE;
      delete process.env.WAYLAND_DISPLAY;
      service.showKioskOverlay({
        cafeName: 'Test',
        announcements: [],
        callStaffEnabled: true,
        sessionActive: false,
      });
      const mockWindow = (service as any).kioskWindow;
      expect(mockWindow.setKiosk).not.toHaveBeenCalled();
      expect(mockWindow.maximize).not.toHaveBeenCalled();
      expect(mockWindow.setAlwaysOnTop).not.toHaveBeenCalledWith(true, 'screen-saver');
    });
  });

  describe('Screenshot fallback on Wayland', () => {
    it('throws clear error when no screen sources available', async () => {
      vi.mocked(desktopCapturer.getSources).mockResolvedValueOnce([]);
      await expect(service.captureScreenshot()).rejects.toThrow(/Screenshot unavailable/);
    });

    it('throws when thumbnail not available', async () => {
      vi.mocked(desktopCapturer.getSources).mockResolvedValueOnce([{ id: 'screen:0:0', name: 'Screen 1', thumbnail: null }]);
      await expect(service.captureScreenshot()).rejects.toThrow(/Screenshot thumbnail not available/);
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agent && npx vitest run tests/platform/linux.test.ts -v
```
Expected: FAIL - tests don't exist yet

- [ ] **Step 3: Add tests to linux.test.ts**

Append the test code above to the existing `agent/tests/platform/linux.test.ts` file.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd agent && npx vitest run tests/platform/linux.test.ts -v
```
Expected: PASS - all Wayland tests pass

- [ ] **Step 5: Commit**

```bash
git add agent/tests/platform/linux.test.ts
git commit -m "test(linux): add Wayland detection, kiosk flags, screenshot fallback tests"
```

---

## Task 5: Auto-Start Production Unit Files

**Files:**
- Create: `docs/autostart/arcade-agent.service` (production systemd)
- Create: `docs/autostart/com.arcade.agent.plist` (production LaunchAgent)
- Modify: `docs/autostart/arcade-agent.desktop` (verify content)

**Interfaces:**
- Consumes: Reference templates from spec
- Produces: Production-ready unit files for all 3 OSes

- [ ] **Step 1: Write production systemd service file**

```ini
# docs/autostart/arcade-agent.service
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

- [ ] **Step 2: Write production LaunchAgent plist**

```xml
<!-- docs/autostart/com.arcade.agent.plist -->
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

- [ ] **Step 3: Verify/update XDG desktop entry**

```ini
# docs/autostart/arcade-agent.desktop
[Desktop Entry]
Type=Application
Name=Arcade Agent
Exec=/opt/arcade-agent/arcade-agent
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
```

- [ ] **Step 4: Commit**

```bash
git add docs/autostart/arcade-agent.service docs/autostart/com.arcade.agent.plist docs/autostart/arcade-agent.desktop
git commit -m "docs(autostart): add production systemd, LaunchAgent, XDG unit files"
```

---

## Task 6: Auto-Start Integration Tests

**Files:**
- Create: `agent/tests/platform/autostart.test.ts`
- Create: `frontend/src/components/AutoStartToggle.test.tsx` (or extend existing)

**Interfaces:**
- Consumes: Platform service mocks, WebSocket command mocks
- Produces: Tests for enableAutoStart/disableAutoStart per OS, frontend toggle

- [ ] **Step 1: Write autostart.test.ts**

```typescript
// agent/tests/platform/autostart.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WindowsPlatformService } from '../../src/main/platform/windows.js';
import { LinuxPlatformService } from '../../src/main/platform/linux.js';
import { MacOSPlatformService } from '../../src/main/platform/macos.js';
import { exec } from 'child_process';
import * as fs from 'node:fs/promises';

vi.mock('child_process', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, exec: vi.fn().mockImplementation((_, optionsOrCallback, maybeCallback) => { const callback = typeof optionsOrCallback === 'function' ? optionsOrCallback : maybeCallback; if (callback) callback(null, 'stdout', 'stderr'); return undefined; }) };
});

const mockFs = vi.hoisted(() => ({ mkdir: vi.fn().mockResolvedValue(undefined), writeFile: vi.fn().mockResolvedValue(undefined), rm: vi.fn().mockResolvedValue(undefined) }));
vi.mock('node:fs', () => ({ default: { promises: mockFs }, promises: mockFs }));

describe('Auto-Start - Windows', () => {
  let service: WindowsPlatformService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new WindowsPlatformService();
  });

  it('enableAutoStart writes to HKCU Run registry', async () => {
    // Mock isTestMode to return false for this test
    vi.doMock('../../src/main/platform/safety.js', () => ({ isTestMode: () => false }), { virtual: true });
    await service.enableAutoStart();
    expect(exec).toHaveBeenCalledWith(expect.stringContaining('reg.exe add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"'), expect.any(Function));
  });

  it('disableAutoStart removes from HKCU Run registry', async () => {
    vi.doMock('../../src/main/platform/safety.js', () => ({ isTestMode: () => false }), { virtual: true });
    await service.disableAutoStart();
    expect(exec).toHaveBeenCalledWith(expect.stringContaining('reg.exe delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"'), expect.any(Function));
  });
});

describe('Auto-Start - Linux', () => {
  let service: LinuxPlatformService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new LinuxPlatformService();
  });

  it('enableAutoStart writes .desktop file to ~/.config/autostart/', async () => {
    vi.doMock('../../src/main/platform/safety.js', () => ({ isTestMode: () => false }), { virtual: true });
    await service.enableAutoStart();
    expect(mockFs.mkdir).toHaveBeenCalledWith(expect.stringContaining('.config/autostart'), { recursive: true });
    expect(mockFs.writeFile).toHaveBeenCalledWith(expect.stringContaining('arcade-agent.desktop'), expect.stringContaining('Exec='), { mode: 0o644 });
  });

  it('disableAutoStart removes .desktop file', async () => {
    vi.doMock('../../src/main/platform/safety.js', () => ({ isTestMode: () => false }), { virtual: true });
    await service.disableAutoStart();
    expect(mockFs.rm).toHaveBeenCalledWith(expect.stringContaining('arcade-agent.desktop'), { force: true });
  });
});

describe('Auto-Start - macOS', () => {
  let service: MacOSPlatformService;

  beforeEach(() => {
    vi.clearAllMocks();
    service = new MacOSPlatformService();
  });

  it('enableAutoStart writes plist to ~/Library/LaunchAgents/', async () => {
    vi.doMock('../../src/main/platform/safety.js', () => ({ isTestMode: () => false }), { virtual: true });
    await service.enableAutoStart();
    expect(mockFs.mkdir).toHaveBeenCalledWith(expect.stringContaining('Library/LaunchAgents'), { recursive: true });
    expect(mockFs.writeFile).toHaveBeenCalledWith(expect.stringContaining('com.neurotech.arcade.agent.plist'), expect.stringContaining('ProgramArguments'), { mode: 0o644 });
  });

  it('disableAutoStart removes plist', async () => {
    vi.doMock('../../src/main/platform/safety.js', () => ({ isTestMode: () => false }), { virtual: true });
    await service.disableAutoStart();
    expect(mockFs.rm).toHaveBeenCalledWith(expect.stringContaining('com.neurotech.arcade.agent.plist'), { force: true });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agent && npx vitest run tests/platform/autostart.test.ts -v
```
Expected: FAIL - test file doesn't exist

- [ ] **Step 3: Create test file**

Write the test code above to `agent/tests/platform/autostart.test.ts`.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd agent && npx vitest run tests/platform/autostart.test.ts -v
```
Expected: PASS - all auto-start tests pass

- [ ] **Step 5: Commit**

```bash
git add agent/tests/platform/autostart.test.ts
git commit -m "test(autostart): add enableAutoStart/disableAutoStart tests for all 3 OSes"
```

---

## Task 7: Frontend Auto-Start Toggle Test

**Files:**
- Create: `frontend/src/components/AutoStartToggle.test.tsx`

**Interfaces:**
- Consumes: WebSocket store, feature flag store
- Produces: Test for Settings → Agent → Auto-Start toggle

- [ ] **Step 1: Write frontend test**

```tsx
// frontend/src/components/AutoStartToggle.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AutoStartToggle } from './AutoStartToggle'; // or wherever it lives

vi.mock('../store/websocketStore', () => ({
  useWebSocketStore: () => ({
    send: vi.fn(),
    isConnected: true,
  }),
}));

vi.mock('../store/featureFlagStore', () => ({
  useFeatureFlagStore: () => ({
    isEnabled: () => true,
  }),
}));

describe('AutoStartToggle', () => {
  const mockSend = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders toggle for admin users', () => {
    render(<AutoStartToggle seatId="seat_001" isAdmin={true} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
  });

  it('does not render for cashier users', () => {
    render(<AutoStartToggle seatId="seat_001" isAdmin={false} />);
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  it('sends SET_AUTO_START true when toggled on', async () => {
    render(<AutoStartToggle seatId="seat_001" isAdmin={true} />);
    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle);
    expect(mockSend).toHaveBeenCalledWith('SET_AUTO_START', { seat_id: 'seat_001', enabled: true });
  });

  it('sends SET_AUTO_START false when toggled off', async () => {
    render(<AutoStartToggle seatId="seat_001" isAdmin={true} />);
    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle); // on
    fireEvent.click(toggle); // off
    expect(mockSend).toHaveBeenLastCalledWith('SET_AUTO_START', { seat_id: 'seat_001', enabled: false });
  });
});
```

- [ ] **Step 2: Run test**

```bash
cd frontend && npx vitest run src/components/AutoStartToggle.test.tsx -v
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AutoStartToggle.test.tsx
git commit -m "test(frontend): add AutoStartToggle test for Settings → Agent → Auto-Start"
```

---

## Task 8: Documentation Updates & Checklists

**Files:**
- Modify: `docs/agent-setup.md` (limitations, auto-start, Wayland)
- Create: `docs/checklists/AC-13_macos_kiosk_checklist.md`
- Create: `docs/checklists/AC-14_macos_remote_commands_checklist.md`
- Create: `docs/checklists/AC-15_macos_launcher_checklist.md`
- Create: `docs/checklists/AC-13_linux_wayland_kiosk_checklist.md`
- Create: `docs/checklists/AC-13_linux_autostart_checklist.md`

**Interfaces:**
- Consumes: Spec requirements
- Produces: Updated docs, hardware verification checklists

- [ ] **Step 1: Update docs/agent-setup.md**

Add/update sections:
- macOS Known Limitations table (Cmd+Tab, Cmd+Space, Force Quit, Ctrl+Cmd+Power)
- Auto-Start: replace reference templates with production files + install commands
- Wayland: GNOME/KDE quirks, X11 fallback commands, screenshot portal

- [ ] **Step 2: Create macOS kiosk checklist**

```markdown
# AC-13 macOS Kiosk Overlay Verification Checklist

**Date:** ___________ **Tester:** ___________ **macOS Version:** ___________

| # | Test | Expected | Actual | Notes |
|---|------|----------|--------|-------|
| 1 | Overlay displays full-screen | ✅ | | |
| 2 | Cmd+Q blocked | ✅ | | |
| 3 | Cmd+W blocked | ✅ | | |
| 4 | Cmd+H blocked | ✅ | | |
| 5 | Cmd+M blocked | ✅ | | |
| 6 | Cmd+Tab | ❌ OS-protected | | Document |
| 7 | Cmd+Space (Spotlight) | ❌ OS-protected | | Document |
| 8 | Cmd+Opt+Esc (Force Quit) | ❌ OS-protected | | Document |
| 9 | Ctrl+Cmd+Power | ❌ OS-protected | | Document |
| 10 | Screen Recording permission granted | ✅ | | Required for screenshots |
| 11 | Accessibility permission granted | ✅ | | Required for shortcut blocking |
| 12 | Session start → overlay hides | ✅ | | |
| 13 | Session end → overlay shows | ✅ | | |
| 14 | Screenshot request returns image | ✅ | | |
| 15 | Auto-start survives reboot | ✅ | | |

**Sign-off:** ___________ **Date:** ___________
```

- [ ] **Step 3: Create macOS remote commands checklist**

```markdown
# AC-14 macOS Remote Commands Verification Checklist

**Date:** ___________ **Tester:** ___________

| # | Command | Method | Expected | Actual |
|---|---------|--------|----------|--------|
| 1 | Restart | `osascript -e 'tell app "System Events" to restart'` | Agent restarts, reconnects | |
| 2 | Shutdown | `osascript -e 'tell app "System Events" to shut down'` | Machine powers off | |
| 3 | Screenshot | `desktopCapturer` + `sharp` | JPEG ≤1280×720, q80 | |
| 4 | Fallback shutdown | `sudo shutdown -h now` (with sudoers) | Works if osascript fails | |

**sudoers entry:** `arcade-agent ALL=(ALL) NOPASSWD: /sbin/shutdown`

**Sign-off:** ___________ **Date:** ___________
```

- [ ] **Step 4: Create macOS launcher checklist**

```markdown
# AC-15 macOS Launcher Verification Checklist

**Date:** ___________ **Tester:** ___________

| # | Step | Expected | Actual |
|---|------|----------|--------|
| 1 | `brew install python-tk` | Tcl/Tk headers installed | |
| 2 | `python build.py --only launcher` | Produces `dist/Arcade Launcher.app/` | |
| 3 | Run `./dist/Arcade Launcher.app/Contents/MacOS/Arcade Launcher --self-test` | Self-test passes | |
| 4 | Tkinter UI renders | Activation/Setup/Main screens show | |
| 5 | "Start Server" spawns uvicorn subprocess | Server accessible on port 8742 | |
| 6 | "Stop Server" terminates uvicorn | Process exits cleanly | |

**Sign-off:** ___________ **Date:** ___________
```

- [ ] **Step 5: Create Linux Wayland checklist**

```markdown
# AC-13 Linux Wayland Kiosk Verification Checklist

**Date:** ___________ **Tester:** ___________ **Distro/DE:** ___________

| # | Environment | Overlay Displays | Bypass-Proof | Screenshots | Notes |
|---|-------------|------------------|--------------|-------------|-------|
| 1 | GNOME Wayland (Ubuntu 24.04) | | ❌ | Portal | |
| 2 | KDE Wayland (Kubuntu 24.04) | | ❌ | Portal | |
| 3 | X11 + Cage | ✅ | ✅ | ✅ | Recommended |
| 4 | X11 + gnome-kiosk | ✅ | ✅ | ✅ | |
| 5 | X11 + ubuntu-frame | ✅ | ✅ | ✅ | |

**Compositor quirks observed:**
- GNOME: _________________________________
- KDE: __________________________________

**Sign-off:** ___________ **Date:** ___________
```

- [ ] **Step 6: Create Linux auto-start checklist**

```markdown
# AC-13 Linux Auto-Start Verification Checklist

**Date:** ___________ **Tester:** ___________ **Distro:** ___________

| # | Test | Expected | Actual |
|---|------|----------|--------|
| 1 | `systemctl --user enable --now arcade-agent.service` | Service enabled | |
| 2 | Reboot machine | Agent starts automatically | |
| 3 | Agent connects to server | WebSocket connected | |
| 4 | Kiosk overlay shows | AVAILABLE state | |
| 5 | Health metrics reported | Within 60s | |
| 6 | `journalctl --user -u arcade-agent` | No errors | |

**Sign-off:** ___________ **Date:** ___________
```

- [ ] **Step 7: Commit**

```bash
git add docs/agent-setup.md docs/checklists/
git commit -m "docs: update agent-setup.md + add hardware verification checklists (M.2-M.6)"
```

---

## Task 9: Final Verification & TODO Update

**Files:**
- Modify: `docs/TODO.md` (mark M.1–M.6 complete)
- Modify: `docs/release/v1.0-acceptance-results.md` (update deferred items)

**Interfaces:**
- Consumes: All previous tasks complete
- Produces: Updated tracking docs

- [ ] **Step 1: Run full test suite**

```bash
make test
make lint
```
Expected: All green

- [ ] **Step 2: Update TODO.md Section M**

Change all `[ ]` to `[x]` for M.1–M.6 with commit references.

- [ ] **Step 3: Update v1.0-acceptance-results.md**

Update deferred items table with verification status.

- [ ] **Step 4: Commit**

```bash
git add docs/TODO.md docs/release/v1.0-acceptance-results.md
git commit -m "docs: mark Section M complete (M.1-M.6)"
```

---
