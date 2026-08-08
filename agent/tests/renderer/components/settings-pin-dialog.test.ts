/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createSettingsPinDialog } from '../../../src/renderer/components/settings-pin-dialog.js';
import { showModal } from '../../../src/renderer/components/low-time-warning.js';

function fireKey(key: string, init: KeyboardEventInit = {}): void {
  document.dispatchEvent(new KeyboardEvent('keydown', { key, cancelable: true, ...init }));
}

describe('createSettingsPinDialog keyboard input', () => {
  let onCancel: ReturnType<typeof vi.fn>;
  let onSuccess: ReturnType<typeof vi.fn>;
  let onVerify: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onCancel = vi.fn();
    onSuccess = vi.fn();
    onVerify = vi.fn().mockResolvedValue(true);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('verifies the typed PIN on Enter and hides on success', async () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('4');
    fireKey('Enter');
    expect(onVerify).toHaveBeenCalledWith('1234');
    await onVerify.mock.results[0].value;
    expect(modal.classList.contains('visible')).toBe(false);
    expect(onSuccess).toHaveBeenCalled();
  });

  it('deletes the last digit on Backspace', async () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('Backspace');
    fireKey('4');
    fireKey('Enter');
    expect(onVerify).toHaveBeenCalledWith('124');
    await onVerify.mock.results[0].value;
  });

  it('closes on Escape and calls onCancel', () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('1');
    fireKey('Escape');
    expect(onCancel).toHaveBeenCalled();
    expect(modal.classList.contains('visible')).toBe(false);
  });

  it('clears the PIN on a wrong PIN and keeps the dialog open', async () => {
    onVerify.mockResolvedValue(false);
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('9');
    fireKey('Enter');
    await onVerify.mock.results[0].value;
    expect(modal.classList.contains('visible')).toBe(true);
    expect(onSuccess).not.toHaveBeenCalled();
    const display = modal.querySelector<HTMLDivElement>('#pin-display')!;
    expect(display.textContent).toBe('');
  });

  it('stops responding to keys after the dialog closes', () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('Escape');
    fireKey('5');
    fireKey('Enter');
    expect(onVerify).not.toHaveBeenCalled();
  });
});
