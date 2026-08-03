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
    onStaffAlertAck: (cb: any) => { handlers['staffAlertAck'] = cb; },
  };
  return handlers;
}

describe('HUD toast notifications', () => {
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  it('showToast creates toast element with message', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    // Mock electronAPI before importing hud
    (window as any).electronAPI = {
      onTimerUpdate: vi.fn(),
      onAnnouncement: vi.fn(),
      onLowTimeWarning: vi.fn(),
      onOverlayContent: vi.fn(),
      onSessionStatus: vi.fn(),
      callStaff: vi.fn(),
      onStaffAlertAck: vi.fn(),
    };
    const { showToast } = await import('../../src/renderer/hud.js');

    showToast('Test message', 3000);

    const toast = document.querySelector('.hud-toast') as HTMLDivElement;
    expect(toast).toBeTruthy();
    expect(toast.textContent).toBe('Test message');
    expect(toast.style.display).toBe('block');
    expect(toast.style.opacity).toBe('1');
  });

  it('showToast auto-dismisses after duration', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    (window as any).electronAPI = {
      onTimerUpdate: vi.fn(),
      onAnnouncement: vi.fn(),
      onLowTimeWarning: vi.fn(),
      onOverlayContent: vi.fn(),
      onSessionStatus: vi.fn(),
      callStaff: vi.fn(),
      onStaffAlertAck: vi.fn(),
    };
    const { showToast } = await import('../../src/renderer/hud.js');

    showToast('Test message', 3000);

    vi.advanceTimersByTime(3000);

    const toast = document.querySelector('.hud-toast') as HTMLDivElement;
    expect(toast.style.opacity).toBe('0');

    vi.advanceTimersByTime(300); // fade out transition

    expect(toast.style.display).toBe('none');
  });

  it('showToast reuses existing toast element', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    (window as any).electronAPI = {
      onTimerUpdate: vi.fn(),
      onAnnouncement: vi.fn(),
      onLowTimeWarning: vi.fn(),
      onOverlayContent: vi.fn(),
      onSessionStatus: vi.fn(),
      callStaff: vi.fn(),
      onStaffAlertAck: vi.fn(),
    };
    const { showToast } = await import('../../src/renderer/hud.js');

    showToast('First', 3000);
    const firstToast = document.querySelector('.hud-toast');

    showToast('Second', 3000);
    const secondToast = document.querySelector('.hud-toast');

    expect(firstToast).toBe(secondToast);
    expect(secondToast?.textContent).toBe('Second');
  });
});

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

  it('shows Call Staff for 5s when the mouse enters the corner', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    handlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    handlers.session('active');
    vi.advanceTimersByTime(35000); // past INTRO
    const btn = document.querySelector('.call-staff-btn') as HTMLElement;
    expect(btn.style.display).toBe('none');
    // hover the hot corner (bottom-right 12%)
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: innerWidth - 10, clientY: innerHeight - 10 }));
    expect(btn.style.display).not.toBe('none');
    // Should show "Call Staff available" toast
    const toast = document.querySelector('.hud-toast') as HTMLDivElement;
    expect(toast?.textContent).toBe('✓ Call Staff available');
    vi.advanceTimersByTime(5000);
    expect(btn.style.display).toBe('none');
  });

  it('extends Call Staff visibility while hovering over button', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    handlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    handlers.session('active');
    vi.advanceTimersByTime(35000); // past INTRO
    const btn = document.querySelector('.call-staff-btn') as HTMLElement;
    expect(btn.style.display).toBe('none');
    // hover the hot corner
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: innerWidth - 10, clientY: innerHeight - 10 }));
    expect(btn.style.display).not.toBe('none');
    // Hover over the button
    btn.dispatchEvent(new MouseEvent('mouseenter'));
    // Advance 5s - button should still be visible because we're hovering
    vi.advanceTimersByTime(5000);
    expect(btn.style.display).not.toBe('none');
    // Leave button
    btn.dispatchEvent(new MouseEvent('mouseleave'));
    // Advance 5s - now should hide
    vi.advanceTimersByTime(5000);
    expect(btn.style.display).toBe('none');
  });

  it('does not show Call Staff when phase is ENDED', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    handlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    // Start active then end session to set phase to ENDED
    handlers.session('active');
    handlers.session('ended');
    const btn = document.querySelector('.call-staff-btn') as HTMLElement;
    expect(btn.style.display).toBe('none');
    // hover the hot corner
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: innerWidth - 10, clientY: innerHeight - 10 }));
    expect(btn.style.display).toBe('none');
  });
});

describe('STAFF_ALERT_ACK toast', () => {
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  it('shows "Staff notified" toast when onStaffAlertAck fires', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    const localHandlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    localHandlers.session('active');

    // Trigger the callback registered by onStaffAlertAck
    localHandlers.staffAlertAck?.();

    const toast = document.querySelector('.hud-toast') as HTMLDivElement;
    expect(toast.textContent).toBe('✓ Staff notified');
    expect(toast.style.display).toBe('block');

    vi.advanceTimersByTime(3000);
    expect(toast.style.opacity).toBe('0');
  });
});

describe('Call Staff full flow', () => {
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  it('hot-zone → click → ACK shows both toasts', async () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="app"></div>';
    vi.resetModules();
    const localHandlers = mockElectronAPI();
    await import('../../src/renderer/hud.js');
    localHandlers.session('active');
    // Advance past INTRO phase (30s) so button is hidden
    vi.advanceTimersByTime(35000);

    const callBtn = document.querySelector('.call-staff-btn') as HTMLButtonElement;
    expect(callBtn.style.display).toBe('none');

    // 1. Hot-zone trigger (use same coordinates as existing test)
    const hoverEvent = new MouseEvent('mousemove', {
      clientX: innerWidth - 10,
      clientY: innerHeight - 10,
    });
    window.dispatchEvent(hoverEvent);

    expect(callBtn.style.display).toBe('block');
    let toast = document.querySelector('.hud-toast') as HTMLDivElement;
    expect(toast.textContent).toBe('✓ Call Staff available');

    // 2. User clicks button
    callBtn.click();

    // Verify callStaff IPC was called
    const { electronAPI } = (window as any);
    expect(electronAPI.callStaff).toHaveBeenCalled();

    // 3. Simulate STAFF_ALERT_ACK from server
    localHandlers.staffAlertAck?.();

    // Should show "Staff notified" toast
    toast = document.querySelector('.hud-toast') as HTMLDivElement;
    expect(toast.textContent).toBe('✓ Staff notified');
  });
});
