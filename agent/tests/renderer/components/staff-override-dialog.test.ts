/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi } from 'vitest';
import { createStaffOverrideDialog } from '../../../src/renderer/components/staff-override-dialog.js';

describe('createStaffOverrideDialog', () => {
  it('renders PIN display and keypad', () => {
    const onOverride = vi.fn();
    const modal = createStaffOverrideDialog({ onOverride });

    const display = modal.querySelector('.pin-display');
    const buttons = modal.querySelectorAll('.pin-pad button');
    expect(display).not.toBeNull();
    expect(buttons.length).toBe(12);
  });

  it('calls onOverride when Enter is clicked with a PIN', () => {
    const onOverride = vi.fn();
    const modal = createStaffOverrideDialog({ onOverride });
    document.body.appendChild(modal);

    // Click 1, 2, 3, then Enter
    modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="2"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="3"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="✓"]')?.click();

    expect(onOverride).toHaveBeenCalledWith('123');
    document.body.innerHTML = '';
  });

  it('clears PIN when Clear is clicked', () => {
    const onOverride = vi.fn();
    const modal = createStaffOverrideDialog({ onOverride });
    document.body.appendChild(modal);

    // Click 1 then Clear
    modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="C"]')?.click();
    // Click Enter — should not call onOverride because PIN is empty
    modal.querySelector<HTMLButtonElement>('[data-key="✓"]')?.click();

    expect(onOverride).not.toHaveBeenCalled();
    document.body.innerHTML = '';
  });

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn();
    const modal = createStaffOverrideDialog({ onOverride: vi.fn(), onCancel });
    document.body.appendChild(modal);

    modal.querySelector<HTMLButtonElement>('#override-cancel')?.click();

    expect(onCancel).toHaveBeenCalled();
    document.body.innerHTML = '';
  });
});
