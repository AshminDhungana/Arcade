import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mockExecAsync = vi.hoisted(() => vi.fn().mockResolvedValue({ stdout: '', stderr: '' }));

vi.mock('../../src/main/platform/macos.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, execAsync: mockExecAsync };
});

vi.mock('electron', async () => {
  const actual = await vi.importActual<object>('electron');
  class MockBrowserWindow {
    webContents = { on: vi.fn(), once: vi.fn(), send: vi.fn(), loadURL: vi.fn() };
    show = vi.fn(); hide = vi.fn(); destroy = vi.fn(); loadFile = vi.fn();
    setIgnoreMouseEvents = vi.fn(); isDestroyed = vi.fn().mockReturnValue(false);
    isVisible = vi.fn().mockReturnValue(true); on = vi.fn();
    getBounds = vi.fn().mockReturnValue({ x: 0, y: 0, width: 1920, height: 1080 });
    constructor(_opts?: Record<string, unknown>) {}
  }
  const mockDesktopCapturer = { getSources: vi.fn().mockResolvedValue([{ id: 'screen:0:0', name: 'Screen 1', thumbnail: { toPNG: vi.fn().mockReturnValue(Buffer.from('fake-png')) } }]) };
  const mockScreen = { getCursorScreenPoint: vi.fn().mockReturnValue({ x: 0, y: 0 }) };
  const mockPowerMonitor = { on: vi.fn(), off: vi.fn() };
  return { ...actual, default: { BrowserWindow: MockBrowserWindow, desktopCapturer: mockDesktopCapturer, screen: mockScreen, powerMonitor: mockPowerMonitor }, BrowserWindow: MockBrowserWindow, desktopCapturer: mockDesktopCapturer, screen: mockScreen, powerMonitor: mockPowerMonitor };
});

vi.mock('sharp', () => ({ default: vi.fn().mockReturnValue({ resize: vi.fn().mockReturnThis(), jpeg: vi.fn().mockReturnThis(), toBuffer: vi.fn().mockResolvedValue(Buffer.from('compressed-jpg')) }) }));
vi.mock('systeminformation', () => ({ default: { cpu: vi.fn().mockResolvedValue({ brand: 'Apple M2', cores: 8 }), mem: vi.fn().mockResolvedValue({ total: 34359738368 }), diskLayout: vi.fn().mockResolvedValue([{ size: 1000000000000 }]) } }));

const mockFs = vi.hoisted(() => ({ mkdir: vi.fn().mockResolvedValue(undefined), writeFile: vi.fn().mockResolvedValue(undefined), rm: vi.fn().mockResolvedValue(undefined) }));
vi.mock('node:fs', () => ({ default: { promises: mockFs }, promises: mockFs }));

import { WindowsPlatformService } from '../../src/main/platform/windows.js';
import { LinuxPlatformService } from '../../src/main/platform/linux.js';
import { MacOSPlatformService } from '../../src/main/platform/macos.js';

describe('Auto-Start - Windows', () => {
  let service: WindowsPlatformService;

  beforeEach(() => {
    vi.clearAllMocks();
    mockExecAsync.mockResolvedValue({ stdout: '', stderr: '' });
    delete process.env.NODE_ENV;
    delete process.env.VITEST;
    service = new WindowsPlatformService();
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
  });

  it('enableAutoStart writes to HKCU Run registry', async () => {
    const execAsyncSpy = vi.spyOn(service as any, 'execAsync').mockResolvedValue({ stdout: '', stderr: '' });
    await service.enableAutoStart();
    expect(execAsyncSpy).toHaveBeenCalledWith(expect.stringContaining('reg.exe add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"'));
    execAsyncSpy.mockRestore();
  });

  it('disableAutoStart removes from HKCU Run registry', async () => {
    const execAsyncSpy = vi.spyOn(service as any, 'execAsync').mockResolvedValue({ stdout: '', stderr: '' });
    await service.disableAutoStart();
    expect(execAsyncSpy).toHaveBeenCalledWith(expect.stringContaining('reg.exe delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"'));
    execAsyncSpy.mockRestore();
  });
});

describe('Auto-Start - Linux', () => {
  let service: LinuxPlatformService;

  beforeEach(() => {
    vi.clearAllMocks();
    mockExecAsync.mockResolvedValue({ stdout: '', stderr: '' });
    delete process.env.NODE_ENV;
    delete process.env.VITEST;
    service = new LinuxPlatformService();
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
  });

  it('enableAutoStart writes .desktop file to autostart dir', async () => {
    await service.enableAutoStart();
    expect(mockFs.mkdir).toHaveBeenCalledWith(expect.any(String), { recursive: true });
    expect(mockFs.writeFile).toHaveBeenCalledWith(expect.any(String), expect.stringContaining('Exec='), { mode: 0o644 });
  });

  it('disableAutoStart removes .desktop file', async () => {
    await service.disableAutoStart();
    expect(mockFs.rm).toHaveBeenCalledWith(expect.any(String), { force: true });
  });
});

describe('Auto-Start - macOS', () => {
  let service: MacOSPlatformService;

  beforeEach(() => {
    vi.clearAllMocks();
    mockExecAsync.mockResolvedValue({ stdout: '', stderr: '' });
    delete process.env.NODE_ENV;
    delete process.env.VITEST;
    service = new MacOSPlatformService();
  });

  afterEach(() => {
    (service as any).stopHotspotPolling?.();
    service.hideKioskOverlay();
  });

  it('enableAutoStart writes plist to LaunchAgents dir', async () => {
    await service.enableAutoStart();
    expect(mockFs.mkdir).toHaveBeenCalledWith(expect.any(String), { recursive: true });
    expect(mockFs.writeFile).toHaveBeenCalledWith(expect.any(String), expect.stringContaining('ProgramArguments'), { mode: 0o644 });
  });

  it('disableAutoStart removes plist', async () => {
    await service.disableAutoStart();
    expect(mockFs.rm).toHaveBeenCalledWith(expect.any(String), { force: true });
  });
});
