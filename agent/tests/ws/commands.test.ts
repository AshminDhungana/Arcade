import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createCommandHandlers, type CommandHandlers } from '../../src/main/ws/commands.js';
import type { IPlatformService } from '../../src/main/platform/types.js';

describe('Command Handlers', () => {
  let mockPlatform: IPlatformService;
  let handlers: CommandHandlers;

  beforeEach(() => {
    mockPlatform = {
      showKioskOverlay: vi.fn(),
      hideKioskOverlay: vi.fn(),
      updateTimer: vi.fn(),
      sendAnnouncement: vi.fn(),
      isKioskVisible: vi.fn().mockReturnValue(false),
      restartPC: vi.fn().mockResolvedValue(undefined),
      shutdownPC: vi.fn().mockResolvedValue(undefined),
      captureScreenshot: vi.fn().mockResolvedValue(Buffer.from('fake-jpg')),
      enableAutoStart: vi.fn().mockResolvedValue(undefined),
      disableAutoStart: vi.fn().mockResolvedValue(undefined),
      getSystemInfo: vi.fn().mockResolvedValue({
        cpuModel: 'Intel i7', cpuCores: 8, totalMemoryGB: 16, totalDiskGB: 512,
        osName: 'win32', osVersion: '10.0.22631', hostname: 'test-pc',
      }),
      showHud: vi.fn(),
      hideHud: vi.fn(),
      showLowTimeWarning: vi.fn(),
    };
    handlers = createCommandHandlers(mockPlatform, { seatId: 'seat_001' });
  });

  it('has handlers for all server command types', () => {
    const expected = [
      'HIDE_OVERLAY', 'SHOW_OVERLAY', 'SHOW_MESSAGE', 'RESTART',
      'SHUTDOWN', 'TAKE_SCREENSHOT', 'LOW_TIME_WARNING', 'RESET_OVERRIDE',
    ];
    for (const cmd of expected) {
      expect(handlers[cmd as keyof typeof handlers]).toBeDefined();
      expect(typeof handlers[cmd as keyof typeof handlers]).toBe('function');
    }
  });

  it('HIDE_OVERLAY calls hideKioskOverlay', () => {
    handlers.HIDE_OVERLAY({ session_id: 'sess-123', started_at: '2026-06-01T10:00:00Z' });
    expect(mockPlatform.hideKioskOverlay).toHaveBeenCalled();
  });

  it('SHOW_OVERLAY calls showKioskOverlay', () => {
    handlers.SHOW_OVERLAY({ session_id: 'sess-123' });
    expect(mockPlatform.showKioskOverlay).toHaveBeenCalledWith({
      cafeName: 'Arcade', announcements: [], callStaffEnabled: true, sessionActive: false,
    });
  });

  it('SHOW_MESSAGE calls sendAnnouncement', () => {
    handlers.SHOW_MESSAGE({ text: 'Hello', duration_seconds: 5 });
    expect(mockPlatform.sendAnnouncement).toHaveBeenCalledWith('Hello', 5000);
  });

  it('RESTART calls restartPC', async () => {
    await handlers.RESTART({ delay_seconds: 10 });
    expect(mockPlatform.restartPC).toHaveBeenCalled();
  });

  it('SHUTDOWN calls shutdownPC', async () => {
    await handlers.SHUTDOWN({ delay_seconds: 10 });
    expect(mockPlatform.shutdownPC).toHaveBeenCalled();
  });

  it('TAKE_SCREENSHOT does not call captureScreenshot (handled by client)', async () => {
    await handlers.TAKE_SCREENSHOT({});
    expect(mockPlatform.captureScreenshot).not.toHaveBeenCalled();
  });

  it('LOW_TIME_WARNING routes to showLowTimeWarning', () => {
    handlers.LOW_TIME_WARNING({ minutes_remaining: 5 });
    expect(mockPlatform.showLowTimeWarning).toHaveBeenCalledWith(5);
  });

  it('RESET_OVERRIDE is a no-op', () => {
    handlers.RESET_OVERRIDE({});
    expect(mockPlatform.hideKioskOverlay).not.toHaveBeenCalled();
    expect(mockPlatform.showKioskOverlay).not.toHaveBeenCalled();
  });
});
