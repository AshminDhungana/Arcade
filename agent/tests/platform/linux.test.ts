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
