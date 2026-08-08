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
import { desktopCapturer } from 'electron';

describe('WindowsPlatformService', () => {
  let service: WindowsPlatformService;
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    service = new WindowsPlatformService();
    vi.clearAllMocks();
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    service.hideKioskOverlay();
    warnSpy.mockRestore();
  });

  it('exposes all IPlatformService methods', () => {
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
});
