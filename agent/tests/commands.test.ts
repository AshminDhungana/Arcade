import { describe, it, expect, vi } from 'vitest';
import { createCommandHandlers } from '../src/main/ws/commands.js';
import type { IPlatformService, OverlayContent } from '../src/main/platform/types.js';

function makeFakePlatform() {
  const calls: { overlay?: OverlayContent; lowTime?: number } = {};
  const platform = {
    showKioskOverlay: (c: OverlayContent) => { calls.overlay = c; },
    hideKioskOverlay: vi.fn(),
    updateTimer: vi.fn(),
    sendAnnouncement: vi.fn(),
    isKioskVisible: () => false,
    restartPC: vi.fn(),
    shutdownPC: vi.fn(),
    captureScreenshot: vi.fn(),
    enableAutoStart: vi.fn(),
    disableAutoStart: vi.fn(),
    getSystemInfo: vi.fn(),
    showLowTimeWarning: (m: number) => { calls.lowTime = m; },
    showHud: vi.fn(),
    hideHud: vi.fn(),
  } as unknown as IPlatformService;
  return { platform, calls };
}

describe('createCommandHandlers', () => {
  it('SHOW_OVERLAY brands with the fetched cafe name', () => {
    const { platform, calls } = makeFakePlatform();
    const handlers = createCommandHandlers(
      platform,
      { seatId: 'seat_001', getCafeName: () => 'Fetched Cafe' },
    );
    handlers.SHOW_OVERLAY({ session_id: 's1' });
    expect(calls.overlay?.cafeName).toBe('Fetched Cafe');
  });

  it('LOW_TIME_WARNING routes to platform.showLowTimeWarning', () => {
    const { platform, calls } = makeFakePlatform();
    const handlers = createCommandHandlers(
      platform,
      { seatId: 'seat_001', getCafeName: () => 'Cafe' },
    );
    handlers.LOW_TIME_WARNING({ minutes_remaining: 5 });
    expect(calls.lowTime).toBe(5);
  });
});
