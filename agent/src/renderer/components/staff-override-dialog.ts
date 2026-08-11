/**
 * Staff override PIN dialog — pure DOM helper.
 *
 * Renders a numeric keypad for PIN entry.  On confirm, calls the
 * `onOverride` callback with the entered PIN.  Supports physical-keyboard
 * entry via `bindPinKeyboard` (digits, Backspace, Enter, Escape).
 */

import { ARCADE_ICON_SVG } from '../icon.js';
import { bindPinKeyboard } from './pin-keyboard.js';

export interface StaffOverrideOptions {
  onOverride: (pin: string) => void;
  onCancel?: () => void;
  onSettings?: () => void;
}

export interface StaffOverrideDialogElement extends HTMLDivElement {
  /** Flash "Wrong PIN" and shake the dialog after a failed verification. */
  _showError?: () => void;
}

/** Build the staff-override modal element with a numeric keypad. */
export function createStaffOverrideDialog(options: StaffOverrideOptions): StaffOverrideDialogElement {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.style.display = 'flex';

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-title"><span class="modal-icon">${ARCADE_ICON_SVG}</span><span>Staff Override</span></div>
      <div class="modal-body">
        <p>Enter staff override PIN:</p>
        <div class="pin-display" id="pin-display"></div>
        <p class="pin-error" id="pin-error" style="display: none;">Wrong PIN — try again</p>
        <div class="pin-pad">
          <button data-key="1">1</button>
          <button data-key="2">2</button>
          <button data-key="3">3</button>
          <button data-key="4">4</button>
          <button data-key="5">5</button>
          <button data-key="6">6</button>
          <button data-key="7">7</button>
          <button data-key="8">8</button>
          <button data-key="9">9</button>
          <button data-key="C">Clear</button>
          <button data-key="0">0</button>
          <button data-key="✓">Enter</button>
        </div>
      </div>
      <div class="modal-actions">
        <button class="modal-btn secondary" id="override-cancel">Cancel</button>
        <button class="modal-btn primary" id="override-confirm">Override</button>
        <button class="modal-btn secondary" id="override-settings">Settings</button>
      </div>
    </div>
  `;

  let pin = '';
  const display = modal.querySelector<HTMLDivElement>('#pin-display')!;
  const errorEl = modal.querySelector<HTMLParagraphElement>('#pin-error')!;

  const updateDisplay = (): void => {
    display.textContent = pin.replace(/./g, '●');
    // Clear the error as soon as the user starts typing again.
    errorEl.style.display = 'none';
  };

  /** Flash "Wrong PIN" and shake the dialog (called on failed verification). */
  const showError = (): void => {
    errorEl.style.display = 'block';
    const content = modal.querySelector<HTMLElement>('.modal-content');
    if (content) {
      content.classList.remove('shake');
      // Force reflow so a repeated shake restarts the animation.
      void content.offsetWidth;
      content.classList.add('shake');
    }
  };

  // Physical-keyboard cleanup, assigned below; used by submit/closeModal.
  let keyboardCleanup: () => void = () => {};

  const submit = (): void => {
    if (pin.length === 0) return;
    options.onOverride(pin);
    pin = '';
    updateDisplay();
    keyboardCleanup();
  };

  const closeModal = (): void => {
    pin = '';
    updateDisplay();
    keyboardCleanup();
    options.onCancel?.();
    modal.classList.remove('visible');
    modal.style.display = 'none';
  };

  // Numeric keypad handler
  const handleKey = (key: string): void => {
    if (key === 'C') {
      pin = '';
    } else if (key === '✓') {
      submit();
      return;
    } else {
      pin += key;
    }
    updateDisplay();
  };

  // Physical-keyboard entry
  keyboardCleanup = bindPinKeyboard(modal, {
    onDigit: (digit) => handleKey(digit),
    onBackspace: () => {
      pin = pin.slice(0, -1);
      updateDisplay();
    },
    onSubmit: submit,
    onCancel: closeModal,
  });
  (modal as HTMLDivElement & { _cleanup?: () => void })._cleanup = keyboardCleanup;

  // Wire keypad buttons
  modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach((btn) => {
    btn.addEventListener('click', () => handleKey(btn.dataset.key || ''));
  });

  // Cancel button
  modal.querySelector<HTMLButtonElement>('#override-cancel')?.addEventListener('click', closeModal);

  // Confirm button
  modal.querySelector<HTMLButtonElement>('#override-confirm')?.addEventListener('click', submit);

  // Settings button
  modal.querySelector<HTMLButtonElement>('#override-settings')?.addEventListener('click', () => {
    options.onSettings?.();
  });

  (modal as StaffOverrideDialogElement)._showError = showError;

  return modal as StaffOverrideDialogElement;
}
