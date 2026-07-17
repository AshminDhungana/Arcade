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
  it('routes timer/announcement/low-time to HUD when a session is active', () => {
    const svc = new WindowsPlatformService();
    const hud = makeWindow();
    const kiosk = makeWindow();
    // @ts-expect-error inject test windows
    svc.hudWindow = hud;
    // @ts-expect-error inject test windows
    svc.kioskWindow = kiosk;
    // @ts-expect-error flip session flag
    svc.sessionActive = true;

    svc.updateTimer({ elapsedSeconds: 300 });
    svc.sendAnnouncement('Hi', 1000);
    svc.showLowTimeWarning(5);

    expect(hud.sent['overlay:timer'][0]).toEqual({ elapsedSeconds: 300 });
    expect(kiosk.sent['overlay:timer']).toBeUndefined();
    expect(hud.sent['overlay:announcement']).toBeTruthy();
    expect(hud.sent['overlay:low-time']).toBeTruthy();
  });
});
