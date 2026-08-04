/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi } from 'vitest';
import { createSettingsPinDialog } from '../../../src/renderer/components/settings-pin-dialog.js';

describe('createSettingsPinDialog', () => {
  it('renders PIN display and keypad', () => {
    const onVerify = vi.fn().mockResolvedValue(true);
    const onCancel = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel });

    const display = modal.querySelector('.pin-display');
    const buttons = modal.querySelectorAll('.pin-pad button');
    expect(display).not.toBeNull();
    expect(buttons.length).toBe(12);
  });

  it('calls onVerify when Unlock is clicked with a PIN', async () => {
    const onVerify = vi.fn().mockResolvedValue(true);
    const onCancel = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel });
    document.body.appendChild(modal);

    // Click 1, 2, 3, 4, then Unlock
    modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="2"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="3"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="4"]')?.click();
    modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

    // Wait for async verification
    await new Promise(r => setTimeout(r, 10));

    expect(onVerify).toHaveBeenCalledWith('1234');
    document.body.innerHTML = '';
  });

  it('clears PIN when Clear is clicked', () => {
    const onVerify = vi.fn().mockResolvedValue(true);
    const onCancel = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel });
    document.body.appendChild(modal);

    // Click 1 then Clear
    modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="C"]')?.click();
    // Click Unlock — should not call onVerify because PIN is empty
    modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

    expect(onVerify).not.toHaveBeenCalled();
    document.body.innerHTML = '';
  });

  it('calls onCancel when backdrop is clicked', () => {
    const onVerify = vi.fn().mockResolvedValue(true);
    const onCancel = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel });
    document.body.appendChild(modal);

    modal.click();

    expect(onCancel).toHaveBeenCalled();
    document.body.innerHTML = '';
  });

  it('calls onCancel when ESC key is pressed', () => {
    const onVerify = vi.fn().mockResolvedValue(true);
    const onCancel = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel });
    document.body.appendChild(modal);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

    expect(onCancel).toHaveBeenCalled();
    document.body.innerHTML = '';
  });

  describe('onSuccess callback', () => {
    it('calls onSuccess when PIN verification succeeds', async () => {
      const onVerify = vi.fn().mockResolvedValue(true);
      const onCancel = vi.fn();
      const onSuccess = vi.fn();
      const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
      document.body.appendChild(modal);

      // Enter PIN: 1-2-3-4
      modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
      modal.querySelector<HTMLButtonElement>('[data-key="2"]')?.click();
      modal.querySelector<HTMLButtonElement>('[data-key="3"]')?.click();
      modal.querySelector<HTMLButtonElement>('[data-key="4"]')?.click();
      // Click Unlock
      modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

      // Wait for async verification
      await new Promise(r => setTimeout(r, 10));

      expect(onSuccess).toHaveBeenCalled();
      document.body.innerHTML = '';
    });

    it('does NOT call onSuccess when PIN verification fails', async () => {
      const onVerify = vi.fn().mockResolvedValue(false);
      const onCancel = vi.fn();
      const onSuccess = vi.fn();
      const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
      document.body.appendChild(modal);

      modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
      modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

      await new Promise(r => setTimeout(r, 10));

      expect(onSuccess).not.toHaveBeenCalled();
      document.body.innerHTML = '';
    });

    it('works when onSuccess is not provided', async () => {
      const onVerify = vi.fn().mockResolvedValue(true);
      const onCancel = vi.fn();
      const modal = createSettingsPinDialog({ onVerify, onCancel });
      document.body.appendChild(modal);

      modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
      modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

      await new Promise(r => setTimeout(r, 10));

      // Should not throw
      document.body.innerHTML = '';
    });
  });
});
