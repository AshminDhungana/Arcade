/**
 * Staff override PIN dialog — pure DOM helper.
 *
 * Renders a numeric keypad for PIN entry.  On confirm, calls the
 * `onOverride` callback with the entered PIN.
 */

export interface StaffOverrideOptions {
  onOverride: (pin: string) => void;
  onCancel?: () => void;
  onSettings?: () => void;
}

/** Build the staff-override modal element with a numeric keypad. */
export function createStaffOverrideDialog(options: StaffOverrideOptions): HTMLDivElement {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.style.display = 'flex';

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-title">🔐 Staff Override</div>
      <div class="modal-body">
        <p>Enter staff override PIN:</p>
        <div class="pin-display" id="pin-display"></div>
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
        <button class="modal-btn" id="override-settings">Settings</button>
      </div>
    </div>
  `;

  let pin = '';
  const display = modal.querySelector<HTMLDivElement>('#pin-display')!;

  const updateDisplay = (): void => {
    display.textContent = pin.replace(/./g, '●');
  };

  // Numeric keypad handler
  const handleKey = (key: string): void => {
    if (key === 'C') {
      pin = '';
    } else if (key === '✓') {
      if (pin.length > 0) {
        options.onOverride(pin);
        pin = '';
        updateDisplay();
      }
      return;
    } else {
      pin += key;
    }
    updateDisplay();
  };

  // Wire keypad buttons
  modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach((btn) => {
    btn.addEventListener('click', () => handleKey(btn.dataset.key || ''));
  });

  // Cancel button
  modal.querySelector<HTMLButtonElement>('#override-cancel')?.addEventListener('click', () => {
    pin = '';
    options.onCancel?.();
    modal.classList.remove('visible');
    modal.style.display = 'none';
    updateDisplay();
  });

  // Confirm button
  modal.querySelector<HTMLButtonElement>('#override-confirm')?.addEventListener('click', () => {
    if (pin.length > 0) {
      options.onOverride(pin);
      pin = '';
      updateDisplay();
    }
  });

  // Settings button
  modal.querySelector<HTMLButtonElement>('#override-settings')?.addEventListener('click', () => {
    options.onSettings?.();
  });

  return modal;
}
