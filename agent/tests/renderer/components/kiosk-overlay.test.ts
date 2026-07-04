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
