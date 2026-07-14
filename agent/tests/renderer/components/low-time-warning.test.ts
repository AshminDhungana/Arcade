/**
 * @vitest-environment jsdom
 */

import { describe, it, expect } from 'vitest';
import { createLowTimeModal, showModal, hideModal, formatCountdown } from '../../../src/renderer/components/low-time-warning.js';

describe('createLowTimeModal', () => {
  it('renders modal with correct minutes text (plural)', () => {
    const modal = createLowTimeModal({ minutesRemaining: 5 });
    expect(modal.textContent).toContain('5 minutes remaining');
  });

  it('renders modal with singular minute text', () => {
    const modal = createLowTimeModal({ minutesRemaining: 1 });
    expect(modal.textContent).toContain('1 minute remaining');
  });

  it('has an OK button', () => {
    const modal = createLowTimeModal({ minutesRemaining: 3 });
    const btn = modal.querySelector('button');
    expect(btn).not.toBeNull();
    expect(btn?.textContent).toBe('OK');
  });

  it('calls onDismiss when OK is clicked', () => {
    const onDismiss = vitest.fn();
    const modal = createLowTimeModal({ minutesRemaining: 5, onDismiss });
    document.body.appendChild(modal);

    const btn = modal.querySelector<HTMLButtonElement>('button')!;
    btn.click();

    expect(onDismiss).toHaveBeenCalled();
    document.body.innerHTML = '';
  });
});

describe('formatCountdown', () => {
  it('formats minutes and seconds as MM:SS', () => {
    expect(formatCountdown(5 * 60)).toBe('05:00');
    expect(formatCountdown(4 * 60 + 59)).toBe('04:59');
    expect(formatCountdown(0)).toBe('00:00');
  });
});

describe('showModal / hideModal', () => {
  it('toggles visible class', () => {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    document.body.appendChild(modal);

    showModal(modal);
    expect(modal.classList.contains('visible')).toBe(true);

    hideModal(modal);
    expect(modal.classList.contains('visible')).toBe(false);

    document.body.innerHTML = '';
  });
});
