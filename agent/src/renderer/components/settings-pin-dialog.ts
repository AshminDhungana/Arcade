/**
 * Settings PIN dialog — pure DOM helper.
 * Reuses staff-override-dialog keypad style for Settings access PIN entry.
 */

import { ARCADE_ICON_SVG } from '../icon.js';

export interface SettingsPinDialogOptions {
  onVerify: (pin: string) => Promise<boolean>;
  onCancel: () => void;
  onSuccess?: () => void;
}

export function createSettingsPinDialog(options: SettingsPinDialogOptions): HTMLDivElement {
  const { onVerify, onCancel, onSuccess } = options;

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.style.display = 'flex';

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-title"><span class="modal-icon">${ARCADE_ICON_SVG}</span><span>Settings Access</span></div>
      <div class="modal-body">
        <p>Enter staff override PIN to access settings:</p>
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
          <button data-key="✓" id="pin-confirm">Unlock</button>
        </div>
      </div>
    </div>
  `;

  let pin = '';
  const display = modal.querySelector<HTMLDivElement>('#pin-display')!;
  const confirmBtn = modal.querySelector<HTMLButtonElement>('#pin-confirm')!;

  const updateDisplay = (): void => {
    display.textContent = pin.replace(/./g, '●');
  };

  const handleKey = (key: string): void => {
    if (key === 'C') {
      pin = '';
    } else if (key === '✓') {
      if (pin.length > 0) {
        // Disable buttons during verification
        confirmBtn.disabled = true;
        modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = true);

        onVerify(pin).then((success) => {
          confirmBtn.disabled = false;
          modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = false);

          if (success) {
            pin = '';
            updateDisplay();
            modal.classList.remove('visible');
            modal.style.display = 'none';
            onSuccess?.();
          } else {
            // Wrong PIN: shake animation
            modal.querySelector('.modal-content')?.classList.add('shake');
            setTimeout(() => {
              modal.querySelector('.modal-content')?.classList.remove('shake');
            }, 300);
            pin = '';
            updateDisplay();
          }
        });
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

  // Cancel on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      onCancel();
      modal.classList.remove('visible');
      modal.style.display = 'none';
      pin = '';
      updateDisplay();
    }
  });

  // ESC key handler
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel();
      modal.classList.remove('visible');
      modal.style.display = 'none';
      pin = '';
      updateDisplay();
      document.removeEventListener('keydown', handleEsc);
    }
  };
  document.addEventListener('keydown', handleEsc);

  // Store cleanup
  (modal as HTMLDivElement & { _cleanup?: () => void })._cleanup = () => document.removeEventListener('keydown', handleEsc);

  return modal;
}