/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay center brand', () => {
  let container: HTMLDivElement;
  let overlay: KioskOverlay;

  const brandText = (): string =>
    overlay.container.querySelector('.cafe-brand')?.textContent ?? '';

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    overlay = new KioskOverlay(container);
  });

  afterEach(() => {
    overlay.destroy();
    document.body.innerHTML = '';
  });

  it('shows the default fallback name when nothing is set', () => {
    expect(brandText()).toBe('Arcade');
  });

  it('shows the server-provided cafe name in the center brand', () => {
    overlay.setCafeName('Galaxy Lounge');
    expect(brandText()).toBe('Galaxy Lounge');
  });

  it('falls back to Arcade when setCafeName receives an empty name', () => {
    overlay.setCafeName('   ');
    expect(brandText()).toBe('Arcade');
  });

  it('shows the fallback name set by setArcadeName', () => {
    overlay.setArcadeName('My Cafe');
    expect(brandText()).toBe('My Cafe');
  });

  it('server name overrides the fallback name', () => {
    overlay.setArcadeName('My Cafe');
    overlay.setCafeName('Galaxy Lounge');
    expect(brandText()).toBe('Galaxy Lounge');
  });
});

describe('KioskOverlay hotspot (main-process cursor polling)', () => {
  let container: HTMLDivElement;
  let overlay: KioskOverlay;
  let btn: HTMLButtonElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    overlay = new KioskOverlay(container);
    btn = overlay.container.querySelector('.kiosk-btn.primary') as HTMLButtonElement;
  });

  afterEach(() => {
    overlay.destroy();
    document.body.innerHTML = '';
  });

  it('setHotspotActive(true) shows the Call Staff button', () => {
    overlay.setHotspotActive(true);
    expect(btn.classList.contains('visible')).toBe(true);
  });

  it('setHotspotActive(true) reports the hotspot to the click-through callback', () => {
    const seen: boolean[] = [];
    overlay.onHotspotHover((a) => seen.push(a));
    overlay.setHotspotActive(true);
    expect(seen).toEqual([true]);
  });

  it('setHotspotActive(false) while the button is visible keeps the hotspot until it hides', () => {
    const seen: boolean[] = [];
    overlay.onHotspotHover((a) => seen.push(a));
    overlay.setHotspotActive(true);
    overlay.setHotspotActive(false);
    expect(btn.classList.contains('visible')).toBe(true);
    expect(seen).toEqual([true]);
  });

  it('setHotspotActive(false) with no visible button is a no-op (hotspot already off)', () => {
    const seen: boolean[] = [];
    overlay.onHotspotHover((a) => seen.push(a));
    overlay.setHotspotActive(false);
    expect(seen).toEqual([]);
  });

  it('auto-hides the button after 3s and then turns the hotspot off', () => {
    vi.useFakeTimers();
    try {
      const seen: boolean[] = [];
      overlay.onHotspotHover((a) => seen.push(a));
      overlay.setHotspotActive(true);
      expect(btn.classList.contains('visible')).toBe(true);

      overlay.setHotspotActive(false);
      vi.advanceTimersByTime(3000);
      expect(btn.classList.contains('visible')).toBe(false);
      expect(seen).toEqual([true, false]);
    } finally {
      vi.useRealTimers();
    }
  });

  it('clicking the button hides it and turns the hotspot off', () => {
    const seen: boolean[] = [];
    overlay.onHotspotHover((a) => seen.push(a));
    overlay.setHotspotActive(true);
    btn.click();
    expect(btn.classList.contains('visible')).toBe(false);
    expect(seen).toEqual([true, false]);
  });

  it('hovering the button keeps it visible despite a hotspot-off report', () => {
    vi.useFakeTimers();
    try {
      overlay.setHotspotActive(true);
      btn.dispatchEvent(new MouseEvent('mouseenter', { bubbles: false }));
      overlay.setHotspotActive(false);
      vi.advanceTimersByTime(5000);
      expect(btn.classList.contains('visible')).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('setMinimalMode(false) hides the button and clears the hotspot', () => {
    const seen: boolean[] = [];
    overlay.onHotspotHover((a) => seen.push(a));
    overlay.setHotspotActive(true);
    overlay.setMinimalMode(false);
    expect(btn.classList.contains('visible')).toBe(false);
    expect(seen).toEqual([true, false]);
  });
});
