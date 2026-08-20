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
    const preventDefault = vi.fn();
    // Debug: log what shortcut would be generated
    const input = { key: 'q', meta: true, control: false, alt: false, shift: false };
    const shortcut = [
      input.alt ? 'Alt' : '',
      input.control ? 'Control' : '',
      input.shift ? 'Shift' : '',
      input.meta ? 'Meta' : '',
      input.key,
    ].filter(Boolean).join('+');
    console.log('Test shortcut:', shortcut);
    console.log('BLOCKED_SHORTCUTS would match:', ['Meta+q', 'Meta+w', 'Meta+h', 'Meta+m', 'Meta+Shift+i', 'Control+Shift+i', 'Control+p', 'F12', 'F11', 'Escape'].includes(shortcut));
    // Handler signature: (event, input) - event has preventDefault
    handler?.({ preventDefault }, input);
    expect(preventDefault).toHaveBeenCalled();
  });

  it('blocks Cmd+W (Meta+W)', () => {
    const handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    const preventDefault = vi.fn();
    handler?.({ preventDefault }, { key: 'w', meta: true, control: false, alt: false, shift: false });
    expect(preventDefault).toHaveBeenCalled();
  });

  it('blocks Cmd+H (Meta+H)', () => {
    const handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    const preventDefault = vi.fn();
    handler?.({ preventDefault }, { key: 'h', meta: true, control: false, alt: false, shift: false });
    expect(preventDefault).toHaveBeenCalled();
  });

  it('blocks Cmd+M (Meta+M)', () => {
    const handler = vi.mocked(mockWebContents.on).mock.calls.find((c) => c[0] === 'before-input-event')?.[1];
    const preventDefault = vi.fn();
    handler?.({ preventDefault }, { key: 'm', meta: true, control: false, alt: false, shift: false });
    expect(preventDefault).toHaveBeenCalled();
  });
});
