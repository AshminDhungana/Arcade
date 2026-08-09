/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
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
