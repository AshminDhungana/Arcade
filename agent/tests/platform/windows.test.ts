import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mockWebContents = {
  on: vi.fn(),
  send: vi.fn(),
  loadURL: vi.fn(),
};

const mockWindow = {
  webContents: mockWebContents,
  show: vi.fn(),
  hide: vi.fn(),
  destroy: vi.fn(),
  isDestroyed: vi.fn().mockReturnValue(false),
};

vi.mock('electron', async () => {
  const actual = await vi.importActual<object>('electron');
  return {
    ...actual,
    BrowserWindow: vi.fn().mockImplementation(() => ({ ...mockWindow })),
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

import { WindowsPlatformService } from '../../src/main/platform/windows.js';
import { exec } from 'child_process';

describe('WindowsPlatformService', () => {
  let service: WindowsPlatformService;

  beforeEach(() => {
    service = new WindowsPlatformService();
    vi.clearAllMocks();
  });

  afterEach(() => {
    service.hideKioskOverlay();
  });

  it('exposes all IPlatformService methods', () => {
    const expected = [
      'showKioskOverlay',
      'hideKioskOverlay',
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

  it('calls exec with shutdown /r /t 0 on restartPC', async () => {
    await service.restartPC();
    expect(exec).toHaveBeenCalledWith(
      'shutdown /r /t 0',
      expect.any(Function),
    );
  });

  it('calls exec with shutdown /s /t 0 on shutdownPC', async () => {
    await service.shutdownPC();
    expect(exec).toHaveBeenCalledWith(
      'shutdown /s /t 0',
      expect.any(Function),
    );
  });

  it('returns a Buffer from captureScreenshot', async () => {
    const result = await service.captureScreenshot();
    expect(Buffer.isBuffer(result)).toBe(true);
  });

  it('registers auto-start via reg.exe add', async () => {
    await service.enableAutoStart();
    expect(exec).toHaveBeenCalledWith(
      expect.stringContaining('reg.exe add'),
      expect.any(Function),
    );
  });

  it('removes auto-start via reg.exe delete', async () => {
    await service.disableAutoStart();
    expect(exec).toHaveBeenCalledWith(
      expect.stringContaining('reg.exe delete'),
      expect.any(Function),
    );
  });

  it('getSystemInfo returns expected shape', async () => {
    const info = await service.getSystemInfo();
    expect(info).toHaveProperty('cpuModel');
    expect(info).toHaveProperty('cpuCores');
    expect(info).toHaveProperty('totalMemoryGB');
    expect(info).toHaveProperty('totalDiskGB');
    expect(info).toHaveProperty('osName');
    expect(info).toHaveProperty('osVersion');
    expect(info).toHaveProperty('hostname');
  });
});
