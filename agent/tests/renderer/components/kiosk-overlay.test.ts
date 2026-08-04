/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay', () => {
  let parent: HTMLDivElement;
  let overlay: KioskOverlay;

  beforeEach(() => {
    parent = document.createElement('div');
    document.body.appendChild(parent);
    overlay = new KioskOverlay(parent);
  });

  afterEach(() => {
    overlay.destroy();
    document.body.innerHTML = '';
  });

  it('renders the kiosk overlay with clock element', () => {
    const clock = parent.querySelector('.clock');
    expect(clock).not.toBeNull();
  });

  it('renders session indicator', () => {
    const indicator = parent.querySelector('.session-indicator');
    expect(indicator).not.toBeNull();
  });

  it('shows session indicator when session is active', () => {
    overlay.setSessionActive(true);
    const indicator = parent.querySelector('.session-indicator');
    expect(indicator?.classList.contains('active')).toBe(true);
  });

  it('hides session indicator when session is inactive', () => {
    overlay.setSessionActive(true);
    overlay.setSessionActive(false);
    const indicator = parent.querySelector('.session-indicator');
    expect(indicator?.classList.contains('active')).toBe(false);
  });

  it('starts and stops the clock', () => {
    expect(overlay.isClockRunning()).toBe(false);
    overlay.startClock();
    expect(overlay.isClockRunning()).toBe(true);
    overlay.stopClock();
    expect(overlay.isClockRunning()).toBe(false);
  });

  it('updates timer text', () => {
    overlay.setTimer('00:05:32');
    const timer = parent.querySelector('.timer-display');
    expect(timer?.textContent).toBe('00:05:32');
  });

  it('clears timer when session becomes inactive', () => {
    overlay.setTimer('00:05:32');
    overlay.setSessionActive(false);
    const timer = parent.querySelector('.timer-display');
    expect(timer?.textContent).toBe('');
  });

  it('removes elements from DOM on destroy', () => {
    overlay.destroy();
    expect(parent.querySelector('.kiosk-overlay')).toBeNull();
  });
});

describe('KioskOverlay branding', () => {
  it('setCafeName renders the cafe name into the brand header', () => {
    const parent = document.createElement('div');
    const overlay = new KioskOverlay(parent);
    overlay.setCafeName('Neon Cafe');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand).not.toBeNull();
    expect(brand!.textContent).toContain('Neon Cafe');
  });
});

describe('KioskOverlay rail', () => {
  it('has no Settings button in rail', () => {
    const root = document.createElement('div');
    new KioskOverlay(root);
    const rail = root.querySelector('.kiosk-rail');
    const buttons = rail?.querySelectorAll('button');
    expect(buttons?.length).toBe(1);
    expect(buttons?.[0].textContent).toBe('Call Staff');
  });
});

describe('KioskOverlay.setEventBanner', () => {
  it('shows the banner with text', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setEventBanner('Weekend Tournament');
    const banner = root.querySelector('.event-banner') as HTMLElement;
    expect(banner).not.toBeNull();
    expect(banner.textContent).toBe('Weekend Tournament');
    expect(banner.style.display).not.toBe('none');
  });

  it('hides the banner when text is empty (default)', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setEventBanner('');
    const banner = root.querySelector('.event-banner') as HTMLElement;
    expect(banner.style.display).toBe('none');
  });

  it('hides the banner when called with no argument', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setEventBanner();
    const banner = root.querySelector('.event-banner') as HTMLElement;
    expect(banner.style.display).toBe('none');
  });

  it('builds the bug + center + rail layout', () => {
    const root = document.createElement('div');
    new KioskOverlay(root);
    expect(root.querySelector('.kiosk-bug')).not.toBeNull();
    expect(root.querySelector('.cafe-wordmark')).not.toBeNull();
    expect(root.querySelector('.status-pill')).not.toBeNull();
    expect(root.querySelector('.kiosk-center')).not.toBeNull();
    expect(root.querySelector('.kiosk-rail')).not.toBeNull();
    expect(root.querySelector('.kiosk-status')).not.toBeNull();
  });

  it('toggles the status pill between OPEN and LIVE', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    const label = () => (root.querySelector('.status-pill .label') as HTMLElement).textContent;
    expect(label()).toBe('OPEN');
    overlay.setSessionActive(true);
    expect(label()).toBe('LIVE');
    expect(root.querySelector('.status-pill')!.classList.contains('live')).toBe(true);
    overlay.setSessionActive(false);
    expect(label()).toBe('OPEN');
  });

  it('shows all content (bug, center, rail) when sessionActive=true', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);

    // Initial state - overlay shows content when sessionActive=false (default)
    expect(root.querySelector('.kiosk-bug')).toBeTruthy();
    expect(root.querySelector('.kiosk-center')).toBeTruthy();
    expect(root.querySelector('.kiosk-rail')).toBeTruthy();
    expect(root.querySelector('.kiosk-btn.primary')).toBeTruthy();

    // Set sessionActive=true - all content should still be visible
    overlay.setSessionActive(true);

    expect(root.querySelector('.kiosk-bug')).toBeTruthy();
    expect(root.querySelector('.kiosk-center')).toBeTruthy();
    expect(root.querySelector('.kiosk-rail')).toBeTruthy();
    expect(root.querySelector('.kiosk-btn.primary')).toBeTruthy();
  });

  it('updates status pill to LIVE when sessionActive=true', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setSessionActive(true);
    const label = root.querySelector('.status-pill .label');
    expect(label?.textContent).toBe('LIVE');
    expect(root.querySelector('.status-pill')?.classList.contains('live')).toBe(true);
  });

  it('updates status pill to OPEN when sessionActive=false', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setSessionActive(true);
    overlay.setSessionActive(false);
    const label = root.querySelector('.status-pill .label');
    expect(label?.textContent).toBe('OPEN');
    expect(root.querySelector('.status-pill')?.classList.contains('live')).toBe(false);
  });
});

describe('KioskOverlay fallback behavior', () => {
  let parent: HTMLDivElement;
  let overlay: KioskOverlay;

  beforeEach(() => {
    parent = document.createElement('div');
    document.body.appendChild(parent);
    overlay = new KioskOverlay(parent);
  });

  afterEach(() => {
    overlay.destroy();
    document.body.innerHTML = '';
  });

  it('shows "Arcade" in center by default (before any setCafeName)', () => {
    const brand = parent.querySelector('.cafe-brand');
    expect(brand).not.toBeNull();
    expect(brand!.textContent).toBe('Arcade');
  });

  it('setArcadeName updates fallback and displays it when no cafe name set', () => {
    overlay.setArcadeName('My Arcade');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('My Arcade');
  });

  it('setCafeName with non-empty name displays that name (overrides fallback)', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('Neon Cafe');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Neon Cafe');
  });

  it('setCafeName with empty name falls back to arcadeName', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Fallback');
  });

  it('setCafeName with only whitespace falls back to arcadeName', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('   ');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Fallback');
  });

  it('setCafeName with logo and name displays both', () => {
    overlay.setCafeName('Neon Cafe', 'logo.png');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Neon Cafe');
    expect(brand!.querySelector('img')).not.toBeNull();
    expect(brand!.querySelector('img')!.src).toContain('logo.png');
  });

  it('setCafeName with logo only (empty name) shows logo + fallback name', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('', 'logo.png');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Fallback');
    expect(brand!.querySelector('img')).not.toBeNull();
  });

  it('calling setArcadeName after setCafeName with server name does NOT override server name', () => {
    overlay.setCafeName('Server Cafe');
    overlay.setArcadeName('New Fallback');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Server Cafe');
  });
});

describe('KioskOverlay trigger zone', () => {
  it('creates trigger zone at bottom-right corner', () => {
    const root = document.createElement('div');
    new KioskOverlay(root);
    const trigger = root.querySelector('.kiosk-trigger-zone');
    expect(trigger).not.toBeNull();
    expect(trigger).toBeInstanceOf(HTMLDivElement);
  });

  it('trigger zone has correct class name', () => {
    const root = document.createElement('div');
    new KioskOverlay(root);
    const trigger = root.querySelector('.kiosk-trigger-zone') as HTMLElement;
    expect(trigger.className).toBe('kiosk-trigger-zone');
  });
});

describe('KioskOverlay call staff button visibility', () => {
  let root: HTMLDivElement;
  let overlay: KioskOverlay;

  beforeEach(() => {
    root = document.createElement('div');
    document.body.appendChild(root);
    overlay = new KioskOverlay(root);
  });

  afterEach(() => {
    overlay.destroy();
    document.body.innerHTML = '';
  });

  it('button is hidden by default (no .visible class)', () => {
    const btn = root.querySelector('.kiosk-btn.primary') as HTMLElement;
    expect(btn.classList.contains('visible')).toBe(false);
  });

  it('hovering trigger zone shows button', () => {
    const trigger = root.querySelector('.kiosk-trigger-zone') as HTMLElement;
    const btn = root.querySelector('.kiosk-btn.primary') as HTMLElement;
    
    trigger.dispatchEvent(new MouseEvent('mouseenter'));
    
    expect(btn.classList.contains('visible')).toBe(true);
    expect(window.getComputedStyle(btn).opacity).toBe('1');
  });

  it('button auto-hides after 3s when mouse leaves trigger', async () => {
    const trigger = root.querySelector('.kiosk-trigger-zone') as HTMLElement;
    const btn = root.querySelector('.kiosk-btn.primary') as HTMLElement;
    
    trigger.dispatchEvent(new MouseEvent('mouseenter'));
    expect(btn.classList.contains('visible')).toBe(true);
    
    trigger.dispatchEvent(new MouseEvent('mouseleave'));
    
    // Wait for auto-hide
    await new Promise(r => setTimeout(r, 3100));
    
    expect(btn.classList.contains('visible')).toBe(false);
  });

  it('hovering button cancels auto-hide', async () => {
    const trigger = root.querySelector('.kiosk-trigger-zone') as HTMLElement;
    const btn = root.querySelector('.kiosk-btn.primary') as HTMLElement;
    
    trigger.dispatchEvent(new MouseEvent('mouseenter'));
    btn.dispatchEvent(new MouseEvent('mouseenter'));
    trigger.dispatchEvent(new MouseEvent('mouseleave'));
    
    // Wait longer than auto-hide delay
    await new Promise(r => setTimeout(r, 3100));
    
    // Button should still be visible
    expect(btn.classList.contains('visible')).toBe(true);
  });

  it('click fires callback, shows toast, hides button', () => {
    const cb = vi.fn();
    overlay.onCallStaff(cb);
    
    const btn = root.querySelector('.kiosk-btn.primary') as HTMLButtonElement;
    btn.classList.add('visible'); // simulate visible
    
    btn.click();
    
    expect(cb).toHaveBeenCalledTimes(1);
    // Toast assertion - check announcement appears
    const toast = root.querySelector('.kiosk-toast') as HTMLElement;
    expect(toast).not.toBeNull();
    expect(toast.textContent).toBe('✓ Staff notified');
    expect(btn.classList.contains('visible')).toBe(false);
  });

  it('destroy clears hide timer', () => {
    const trigger = root.querySelector('.kiosk-trigger-zone') as HTMLElement;
    trigger.dispatchEvent(new MouseEvent('mouseenter'));
    
    overlay.destroy();
    
    // Timer should be cleared - no error thrown
    // If timer wasn't cleared, it would try to access destroyed DOM
  });
});
