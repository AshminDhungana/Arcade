// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

function mockElectronAPI() {
  const handlers: Record<string, (...a: any[]) => void> = {};
  (window as any).electronAPI = {
    onTimerUpdate: (cb: any) => { handlers['timer'] = cb; },
    onAnnouncement: (cb: any) => { handlers['announcement'] = cb; },
    onLowTimeWarning: (cb: any) => { handlers['lowtime'] = cb; },
    onOverlayContent: () => {},
    onSessionStatus: (cb: any) => { handlers['session'] = cb; },
    callStaff: vi.fn(),
  };
  return handlers;
}

describe('HUD renderer (legacy)', () => {
  let handlers: Record<string, (...a: any[]) => void>;

  beforeEach(async () => {
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    handlers = mockElectronAPI();
    const { initHud } = await import('../../src/renderer/hud.js');
    initHud();
    handlers.session('active');
  });

  it('renders the timer and a Call Staff button', () => {
    const timer = document.querySelector('.hud-timer');
    expect(timer).not.toBeNull();
    const btn = document.querySelector('.call-staff-btn') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    btn!.click();
    expect((window as any).electronAPI.callStaff).toHaveBeenCalled();
  });

  it('shows the low-time modal on low-time warning', () => {
    handlers.lowtime(5);
    expect(document.querySelector('.modal-overlay.visible')).not.toBeNull();
  });
});

describe('HUD transient behavior', () => {
  let handlers: Record<string, (...a: any[]) => void>;

  afterEach(() => vi.useRealTimers());

  it('hides the timer after the INTRO window (~5s)', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    handlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    handlers.session('active');
    const timer = document.querySelector('.hud-timer') as HTMLElement;
    expect(timer.style.display).not.toBe('none');
    vi.advanceTimersByTime(5000);
    expect(timer.style.display).toBe('none');
  });

  it('hides Call Staff after the INTRO window (30s)', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    handlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    handlers.session('active');
    const btn = document.querySelector('.call-staff-btn') as HTMLElement;
    expect(btn.style.display).not.toBe('none');
    vi.advanceTimersByTime(30000);
    expect(btn.style.display).toBe('none');
  });

  it('shows Call Staff for 10s when the mouse enters the corner', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    handlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    handlers.session('active');
    vi.advanceTimersByTime(35000); // past INTRO
    const btn = document.querySelector('.call-staff-btn') as HTMLElement;
    expect(btn.style.display).toBe('none');
    // hover the hot corner (bottom-right 64x64)
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: innerWidth - 10, clientY: innerHeight - 10 }));
    expect(btn.style.display).not.toBe('none');
    vi.advanceTimersByTime(10000);
    expect(btn.style.display).toBe('none');
  });
});
