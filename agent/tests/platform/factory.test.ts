import { describe, it, expect, vi } from 'vitest';

// Mock electron so that importing the Windows platform service doesn't
// trigger an Electron binary download / path resolution error.
vi.mock('electron', () => ({
  BrowserWindow: vi.fn().mockImplementation(() => ({
    webContents: {
      on: vi.fn(),
      send: vi.fn(),
      loadURL: vi.fn(),
    },
    show: vi.fn(),
    hide: vi.fn(),
    destroy: vi.fn(),
    isDestroyed: vi.fn().mockReturnValue(false),
  })),
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
}));

// Mock sharp so the screenshot compression path doesn't touch native code.
vi.mock('sharp', () => ({
  default: vi.fn().mockReturnValue({
    resize: vi.fn().mockReturnThis(),
    jpeg: vi.fn().mockReturnThis(),
    toBuffer: vi.fn().mockResolvedValue(Buffer.from('compressed-jpg')),
  }),
}));

// Mock systeminformation so getSystemInfo doesn't touch the real OS.
vi.mock('systeminformation', () => ({
  default: {
    cpu: vi.fn().mockResolvedValue({ brand: 'Intel i7', cores: 8 }),
    rotating: vi.fn(),
    mem: vi.fn().mockResolvedValue({ total: 34359738368 }),
    diskLayout: vi.fn().mockResolvedValue([{ size: 1000000000000 }]),
  },
}));

import { getPlatformService } from '../../src/main/platform/index.js';

describe('getPlatformService', () => {
  const originalPlatform = process.platform;

  afterEach(() => {
    Object.defineProperty(process, 'platform', {
      value: originalPlatform,
    });
  });

  it('throws on unsupported platform', async () => {
    Object.defineProperty(process, 'platform', { value: 'aix' });

    await expect(getPlatformService()).rejects.toThrow(
      'Platform "aix" is not yet supported',
    );
  });

  it('returns a service on win32', async () => {
    Object.defineProperty(process, 'platform', { value: 'win32' });

    const service = await getPlatformService();
    expect(service).toBeDefined();
    expect(service.constructor.name).toBe('WindowsPlatformService');
  });

  it('returns a LinuxPlatformService on linux', async () => {
    Object.defineProperty(process, 'platform', { value: 'linux' });

    const service = await getPlatformService();
    expect(service).toBeDefined();
    expect(service.constructor.name).toBe('LinuxPlatformService');
  });
});
