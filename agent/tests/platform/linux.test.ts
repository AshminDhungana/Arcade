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
    getBounds = vi.fn().mockReturnValue({ x: 0, y: 0, width: 1920, height: 1080 });
    constructor(_opts?: Record<string, unknown>) {}
  }

  const mockDesktopCapturer = {
    getSources: vi.fn().mockResolvedValue([
      {
        id: 'screen:0:0',
        name: 'Screen 1',
        thumbnail: {
          toPNG: vi.fn().mockReturnValue(Buffer.from('fake-png')),
        },
      },
    ]),
  };

  const mockScreen = {
    getCursorScreenPoint: vi.fn().mockReturnValue({ x: 0, y: 0 }),
  };

  return {
    ...actual,
    // The platform source destructures from the default export, so the mock
    // must override `default` too — not just the named exports.
    default: {
      BrowserWindow: MockBrowserWindow,
      desktopCapturer: mockDesktopCapturer,
      screen: mockScreen,
    },
    BrowserWindow: MockBrowserWindow,
    desktopCapturer: mockDesktopCapturer,
    screen: mockScreen,
  };
});

// exec is used via promisify, so the mock must call its callback.
vi.mock('child_process', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
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
  };
});

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

const mockFs = vi.hoisted(() => ({
  mkdir: vi.fn().mockResolvedValue(undefined),
  writeFile: vi.fn().mockResolvedValue(undefined),
  rm: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('node:fs', () => ({
  default: { promises: mockFs },
  promises: mockFs,
}));

import { LinuxPlatformService, isWayland } from '../../src/main/platform/linux.js';
import { exec } from 'child_process';
import { desktopCapturer, screen } from 'electron';

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
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
    warnSpy.mockRestore();
  });

  it('exposes all 15 IPlatformService methods', () => {
    const expected = [
      'showKioskOverlay',
      'hideKioskOverlay',
      'setKioskClickThrough',
      'showLowTimeWarning',
      'isKioskVisible',
      'updateTimer',
      'sendAnnouncement',
      'sendConfigToOverlay',
      'sendToOverlayAndHud',
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

  it('never runs systemctl reboot under test mode (restart-proof)', async () => {
    await service.restartPC();
    expect(exec).not.toHaveBeenCalled();
  });

  it('never runs systemctl poweroff under test mode (restart-proof)', async () => {
    await service.shutdownPC();
    expect(exec).not.toHaveBeenCalled();
  });

  it('returns a Buffer from captureScreenshot', async () => {
    const result = await service.captureScreenshot();
    expect(Buffer.isBuffer(result)).toBe(true);
  });

  it('throws when no screen sources are available (Wayland/PipeWire)', async () => {
    vi.mocked(desktopCapturer.getSources).mockResolvedValueOnce([]);
    await expect(service.captureScreenshot()).rejects.toThrow(/Screenshot unavailable/);
  });

  it('never writes the XDG autostart .desktop file under test mode', async () => {
    await service.enableAutoStart();
    expect(mockFs.mkdir).not.toHaveBeenCalled();
    expect(mockFs.writeFile).not.toHaveBeenCalled();
  });

  it('never removes the .desktop file under test mode', async () => {
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

  it('showKioskOverlay -> hideKioskOverlay -> showKioskOverlay preserves window', () => {
    // First show — creates window
    service.showKioskOverlay({
      cafeName: 'Test',
      announcements: [],
      callStaffEnabled: true,
      sessionActive: false,
    });
    const firstWindow = (service as any).kioskWindow;
    expect(firstWindow).not.toBeNull();

    // Hide — sends minimal, does NOT destroy
    service.hideKioskOverlay();
    expect(firstWindow.isDestroyed()).toBe(false);
    expect((service as any).kioskWindow).toBe(firstWindow);
    expect(mockWebContents.send).toHaveBeenCalledWith('overlay:set-minimal', true);

    // Show again — reuses same window, sends minimal=false
    vi.clearAllMocks();
    service.showKioskOverlay({
      cafeName: 'Test',
      announcements: [],
      callStaffEnabled: true,
      sessionActive: true,
    });
    expect((service as any).kioskWindow).toBe(firstWindow);
    expect(firstWindow.show).toHaveBeenCalled();
    expect(mockWebContents.send).toHaveBeenCalledWith('overlay:set-minimal', false);
    expect(mockWebContents.send).toHaveBeenCalledWith('overlay:update', expect.objectContaining({ sessionActive: true }));
  });

  describe('hotspot cursor polling', () => {
    let send: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      vi.useFakeTimers();
      service = new LinuxPlatformService();
      vi.clearAllMocks();
      service.showKioskOverlay({
        cafeName: 'Test',
        announcements: [],
        callStaffEnabled: true,
        sessionActive: false,
      });
      send = mockWebContents.send;
      send.mockClear();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('full mode: notifies hotspot when cursor enters the bottom-right corner', () => {
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 100, y: 100 });
      vi.advanceTimersByTime(500);
      expect(send).not.toHaveBeenCalledWith('overlay:hotspot', true);

      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1905, y: 1065 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', true);
    });

    it('full mode: notifies hotspot exit when cursor leaves the corner', () => {
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1905, y: 1065 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', true);

      send.mockClear();
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 100, y: 100 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', false);
    });

    it('minimal mode: notifies hotspot along the full right edge', () => {
      service.hideKioskOverlay();
      send.mockClear();

      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1905, y: 500 });
      vi.advanceTimersByTime(500);
      expect(send).toHaveBeenCalledWith('overlay:hotspot', true);
    });

    it('does not notify for a cursor outside the window', () => {
      vi.mocked(screen.getCursorScreenPoint).mockReturnValue({ x: 1920, y: 100 });
      vi.advanceTimersByTime(500);
      expect(send).not.toHaveBeenCalledWith('overlay:hotspot', true);
    });
  });
});
