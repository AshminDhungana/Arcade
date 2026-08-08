/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createStaffOverrideDialog } from '../../../src/renderer/components/staff-override-dialog.js';
import { showModal } from '../../../src/renderer/components/low-time-warning.js';

function fireKey(key: string, init: KeyboardEventInit = {}): void {
  document.dispatchEvent(new KeyboardEvent('keydown', { key, cancelable: true, ...init }));
}

describe('createStaffOverrideDialog keyboard input', () => {
  let onOverride: ReturnType<typeof vi.fn>;
  let onCancel: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onOverride = vi.fn();
    onCancel = vi.fn();
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('submits the typed PIN on Enter', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('4');
    fireKey('Enter');
    expect(onOverride).toHaveBeenCalledWith('1234');
  });

  it('deletes the last digit on Backspace', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('Backspace');
    fireKey('Enter');
    expect(onOverride).toHaveBeenCalledWith('12');
  });

  it('closes the dialog on Escape', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('1');
    fireKey('Escape');
    expect(onCancel).toHaveBeenCalled();
    expect(modal.classList.contains('visible')).toBe(false);
  });

  it('does not submit on Enter with an empty PIN', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('Enter');
    expect(onOverride).not.toHaveBeenCalled();
  });

  it('stops responding to keys after the dialog closes', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('Escape');
    fireKey('5');
    fireKey('Enter');
    expect(onOverride).not.toHaveBeenCalled();
  });
});
