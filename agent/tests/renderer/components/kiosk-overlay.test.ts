import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay.setMinimalMode', () => {
  let container: HTMLElement;
  let overlay: KioskOverlay;

  beforeEach(() => {
    container = document.createElement('div');
    container.id = 'app';
    document.body.appendChild(container);
    overlay = new KioskOverlay(container);
  });

  afterEach(() => {
    overlay.destroy();
    container.remove();
  });

  it('adds minimal class when enabled=true', () => {
    overlay.setMinimalMode(true);
    expect(overlay.container.classList.contains('minimal')).toBe(true);
  });

  it('removes minimal class when enabled=false', () => {
    overlay.setMinimalMode(true);
    overlay.setMinimalMode(false);
    expect(overlay.container.classList.contains('minimal')).toBe(false);
  });

  it('is idempotent - calling twice with same value has no effect', () => {
    overlay.setMinimalMode(true);
    overlay.setMinimalMode(true);
    expect(overlay.container.classList.contains('minimal')).toBe(true);
  });
});
