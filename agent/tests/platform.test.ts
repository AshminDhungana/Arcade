import { describe, it, expect, vi } from 'vitest';
import { WindowsPlatformService } from '../src/main/platform/windows.js';

function makeWindow() {
  const sent: Record<string, unknown[]> = {};
  return {
    isDestroyed: () => false,
    isVisible: () => true,
    show: vi.fn(),
    hide: vi.fn(),
    destroy: vi.fn(),
    loadFile: vi.fn(),
    setIgnoreMouseEvents: vi.fn(),
    webContents: {
      send: (ch: string, data: unknown) => {
        (sent[ch] ??= []).push(data);
      },
      on: vi.fn(),
    },
    on: vi.fn(),
    sent,
  } as any;
}

describe('WindowsPlatformService routing', () => {
  it('routes timer/announcement/low-time to the kiosk window', () => {
    const svc = new WindowsPlatformService();
    const kiosk = makeWindow();
    // @ts-expect-error inject test window
    svc.kioskWindow = kiosk;

    svc.updateTimer({ elapsedSeconds: 300 });
    svc.sendAnnouncement('Hi', 1000);
    svc.showLowTimeWarning(5);

    expect(kiosk.sent['overlay:timer'][0]).toEqual({ elapsedSeconds: 300 });
    expect(kiosk.sent['overlay:announcement'][0]).toEqual({ text: 'Hi', durationMs: 1000 });
    expect(kiosk.sent['overlay:low-time'][0]).toEqual({ minutes: 5 });
  });
});
