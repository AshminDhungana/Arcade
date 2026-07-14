// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from 'vitest';

// The HUD reads window.electronAPI at init time; register stub callbacks
// that record invocations on the module-level `listeners` object.
const listeners: Record<string, (...args: any[]) => void> = {};

import { initHud } from '../../src/renderer/hud.js';

describe('HUD renderer', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="app"></div>';
    (window as any).electronAPI = {
      onOverlayContent: (cb: any) => { listeners.overlay = cb; },
      onTimerUpdate: (cb: any) => { listeners.timer = cb; },
      onAnnouncement: (cb: any) => { listeners.announcement = cb; },
      onLowTimeWarning: (cb: any) => { listeners.lowtime = cb; },
      onSessionStatus: (cb: any) => { listeners.session = cb; },
      callStaff: vi.fn(),
      staffOverride: vi.fn(),
    };
  });

  it('renders the session ticker and a Call Staff button', () => {
    initHud();
    expect(document.querySelector('.hud-session-indicator')).not.toBeNull();
    const btn = document.querySelector('.call-staff-btn') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    btn!.click();
    expect((window as any).electronAPI.callStaff).toHaveBeenCalled();
  });

  it('shows the low-time modal on overlay:low-time', () => {
    initHud();
    listeners.lowtime(5);
    expect(document.querySelector('.modal-overlay.visible')).not.toBeNull();
  });
});
