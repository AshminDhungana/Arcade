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

vi.mock('sharp', () => ({ default: vi.fn().mockReturnValue({ resize: vi.fn().mockReturnThis(), jpeg: vi.fn().mockReturnThis(), toBuffer: vi.fn().mockResolvedValue(Buffer.from('compressed-jpg')) }) }));

vi.mock('systeminformation', () => ({ default: { cpu: vi.fn().mockResolvedValue({ brand: 'Apple M2', cores: 8 }), mem: vi.fn().mockResolvedValue({ total: 34359738368 }), diskLayout: vi.fn().mockResolvedValue([{ size: 1000000000000 }]) } }));

const mockFs = vi.hoisted(() => ({ mkdir: vi.fn().mockResolvedValue(undefined), writeFile: vi.fn().mockResolvedValue(undefined), rm: vi.fn().mockResolvedValue(undefined) }));
vi.mock('node:fs', () => ({ default: { promises: mockFs }, promises: mockFs }));

import { MacOSPlatformService } from '../../src/main/platform/macos.js';
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

  // Shortcut tests
  describe('shortcut blocking', () => {
    const preventDefault = vi.fn();
    const getHandler = () => vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    const testShortcut = (key: string, meta = true, control = false, alt = false, shift = false) => {
      preventDefault.mockClear();
      const handler = getHandler();
      handler?.({ preventDefault }, { key, meta, control, alt, shift });
      return preventDefault;
    };

    beforeEach(() => {
      service = new MacOSPlatformService();
      vi.clearAllMocks();
      service.showKioskOverlay({ cafeName: 'Test', announcements: [], callStaffEnabled: true, sessionActive: false });
    });

    afterEach(() => {
      (service as any).stopHotspotPolling?.();
      service.hideKioskOverlay();
    });

    it('blocks Cmd+Q (Meta+Q)', () => { expect(testShortcut('q', true)).toHaveBeenCalled(); });
    it('blocks Cmd+W (Meta+W)', () => { expect(testShortcut('w', true)).toHaveBeenCalled(); });
    it('blocks Cmd+H (Meta+H)', () => { expect(testShortcut('h', true)).toHaveBeenCalled(); });
    it('blocks Cmd+M (Meta+M)', () => { expect(testShortcut('m', true)).toHaveBeenCalled(); });
    it('blocks Cmd+Shift+I', () => {
      const handler = getHandler();
      const preventDefault = vi.fn();
      handler?.({ preventDefault }, { key: 'i', meta: true, control: false, alt: false, shift: true });
      expect(preventDefault).toHaveBeenCalled();
    });
    it('blocks Ctrl+Shift+I', () => { expect(testShortcut('i', false, true, false, true)).toHaveBeenCalled(); });
    it('blocks Ctrl+P', () => { expect(testShortcut('p', false, true)).toHaveBeenCalled(); });
    it('blocks F12', () => {
      const handler = getHandler();
      const preventDefault = vi.fn();
      handler?.({ preventDefault }, { key: 'F12', meta: false, control: false, alt: false, shift: false });
      expect(preventDefault).toHaveBeenCalled();
    });
    it('blocks F11', () => {
      const handler = getHandler();
      const preventDefault = vi.fn();
      handler?.({ preventDefault }, { key: 'F11', meta: false, control: false, alt: false, shift: false });
      expect(preventDefault).toHaveBeenCalled();
    });
    it('blocks Escape', () => {
      const handler = getHandler();
      const preventDefault = vi.fn();
      handler?.({ preventDefault }, { key: 'Escape', meta: false, control: false, alt: false, shift: false });
      expect(preventDefault).toHaveBeenCalled();
    });
  });

  describe('restart/shutdown', () => {
    let execAsyncSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      delete process.env.NODE_ENV;
      delete process.env.VITEST;
      service = new MacOSPlatformService();
      vi.clearAllMocks();
    });

    afterEach(() => {
      execAsyncSpy.mockRestore();
    });

    it('restartPC calls osascript for restart', async () => {
      execAsyncSpy = vi.spyOn(service as any, 'execAsync').mockResolvedValue({ stdout: '', stderr: '' });
      await service.restartPC();
      expect(execAsyncSpy).toHaveBeenCalledWith("osascript -e 'tell app \"System Events\" to restart'");
      execAsyncSpy.mockRestore();
    });

    it('shutdownPC calls osascript for shutdown', async () => {
      execAsyncSpy = vi.spyOn(service as any, 'execAsync').mockResolvedValue({ stdout: '', stderr: '' });
      await service.shutdownPC();
      expect(execAsyncSpy).toHaveBeenCalledWith("osascript -e 'tell app \"System Events\" to shut down'");
      execAsyncSpy.mockRestore();
    });

    it('does not execute commands in test mode', async () => {
      process.env.NODE_ENV = 'test';
      const testService = new MacOSPlatformService();
      execAsyncSpy = vi.spyOn(testService as any, 'execAsync').mockResolvedValue({ stdout: '', stderr: '' });
      await testService.restartPC();
      await testService.shutdownPC();
      expect(execAsyncSpy).not.toHaveBeenCalled();
      execAsyncSpy.mockRestore();
    });
  });
});
