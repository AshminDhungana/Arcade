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

  const mockPowerMonitor = {
    on: vi.fn(),
    off: vi.fn(),
  };

  return {
    ...actual,
    // The platform source destructures from the default export, so the mock
    // must override `default` too — not just the named exports.
    default: {
      BrowserWindow: MockBrowserWindow,
      desktopCapturer: mockDesktopCapturer,
      screen: mockScreen,
      powerMonitor: mockPowerMonitor,
    },
    BrowserWindow: MockBrowserWindow,
    desktopCapturer: mockDesktopCapturer,
    screen: mockScreen,
    powerMonitor: mockPowerMonitor,
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

import { WindowsPlatformService } from '../../src/main/platform/windows.js';
import { exec } from 'child_process';
import { desktopCapturer, screen, powerMonitor } from 'electron';

describe('WindowsPlatformService', () => {
  let service: WindowsPlatformService;
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    service = new WindowsPlatformService();
    vi.clearAllMocks();
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
    warnSpy.mockRestore();
  });

  it('exposes all IPlatformService methods', () => {
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

  it('never runs shutdown /r /t 0 under test mode (restart-proof)', async () => {
    await service.restartPC();
    expect(exec).not.toHaveBeenCalled();
  });

  it('never runs shutdown /s /t 0 under test mode (restart-proof)', async () => {
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

  it('never writes the registry key under test mode', async () => {
    await service.enableAutoStart();
    expect(exec).not.toHaveBeenCalled();
  });

  it('never removes the registry key under test mode', async () => {
    await service.disableAutoStart();
    expect(exec).not.toHaveBeenCalled();
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

  it('hideKioskOverlay sends overlay:set-minimal=true when window exists', () => {
    service.showKioskOverlay({
      cafeName: 'Test',
      announcements: [],
      callStaffEnabled: true,
      sessionActive: false,
    });

    const mockWindow = (service as any).kioskWindow;
    const mockSend = mockWindow.webContents.send;

    service.hideKioskOverlay();

    expect(mockSend).toHaveBeenCalledWith('overlay:set-minimal', true);
  });

  it('hideKioskOverlay handles missing window gracefully', () => {
    const newService = new WindowsPlatformService();
    // Don't call showKioskOverlay first - window doesn't exist

    expect(() => newService.hideKioskOverlay()).not.toThrow();
    // Should not crash, just log warning
  });

  describe('hotspot cursor polling', () => {
    let service: WindowsPlatformService;
    let send: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      vi.useFakeTimers();
      service = new WindowsPlatformService();
      vi.clearAllMocks();
      service.showKioskOverlay({
        cafeName: 'Test',
        announcements: [],
        callStaffEnabled: true,
        sessionActive: false,
      });
      const mockWindow = (service as any).kioskWindow;
      send = mockWindow.webContents.send;
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

  describe('power monitor events', () => {
    let service: WindowsPlatformService;
    let send: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      service = new WindowsPlatformService();
      vi.clearAllMocks();
      service.showKioskOverlay({
        cafeName: 'Test',
        announcements: [],
        callStaffEnabled: true,
        sessionActive: true,
      });
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
      const suspendHandler = vi.mocked(powerMonitor.on).mock.calls.find(
        (c) => c[0] === 'suspend'
      )?.[1];
      expect(suspendHandler).toBeDefined();
      suspendHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:suspend');
    });

    it('on resume: restores full mode, clears suspended, sends overlay:resume and request-sync', () => {
      const resumeHandler = vi.mocked(powerMonitor.on).mock.calls.find(
        (c) => c[0] === 'resume'
      )?.[1];
      expect(resumeHandler).toBeDefined();
      resumeHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:set-minimal', false);
      expect(send).toHaveBeenCalledWith('overlay:resume');
      expect(send).toHaveBeenCalledWith('overlay:request-sync', undefined);
    });

    it('lock-screen triggers suspend behavior', () => {
      const lockHandler = vi.mocked(powerMonitor.on).mock.calls.find(
        (c) => c[0] === 'lock-screen'
      )?.[1];
      expect(lockHandler).toBeDefined();
      lockHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:suspend');
    });

    it('unlock-screen triggers resume behavior', () => {
      const unlockHandler = vi.mocked(powerMonitor.on).mock.calls.find(
        (c) => c[0] === 'unlock-screen'
      )?.[1];
      expect(unlockHandler).toBeDefined();
      unlockHandler?.();
      expect(send).toHaveBeenCalledWith('overlay:set-minimal', false);
    });
  });
});
