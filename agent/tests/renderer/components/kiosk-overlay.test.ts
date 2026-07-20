/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
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
});
