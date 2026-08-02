/**
 * In-overlay Settings panel — pure DOM, reuses tokens.css modal styles.
 * Reads config from agent.config.json (passed in), shows masked secret.
 * "Re-enroll" triggers existing enrollment flow via IPC.
 */

import { ARCADE_ICON_SVG } from '../icon.js';

export interface SettingsPanelOptions {
  config: {
    serverUrl: string;
    seatId: string;
    agentSecret: string;
  };
  onReEnroll: () => void;
  onClose: () => void;
}

/** Mask a string for display (keep first/last 4 chars). */
function maskSecret(secret: string): string {
  if (secret.length <= 8) return '●'.repeat(secret.length);
  return secret.slice(0, 4) + '●'.repeat(secret.length - 8) + secret.slice(-4);
}

export function createSettingsPanel(options: SettingsPanelOptions): HTMLDivElement {
  const { config, onReEnroll, onClose } = options;
  const { serverUrl, seatId, agentSecret } = config;

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.style.display = 'flex';

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-title"><span class="modal-icon">${ARCADE_ICON_SVG}</span><span>Settings</span></div>
      <div class="modal-body">
        <div class="settings-field">
          <label>Server URL</label>
          <div class="settings-value">${serverUrl}</div>
        </div>
        <div class="settings-field">
          <label>Seat ID</label>
          <div class="settings-value">${seatId}</div>
        </div>
        <div class="settings-field">
          <label>Agent Secret</label>
          <div class="settings-value">${maskSecret(agentSecret)}</div>
        </div>
      </div>
      <div class="modal-actions">
        <button class="modal-btn secondary" id="settings-close">Close</button>
        <button class="modal-btn primary" id="settings-reenroll">Re-enroll</button>
      </div>
    </div>
  `;

  // Close button
  modal.querySelector<HTMLButtonElement>('#settings-close')?.addEventListener('click', () => {
    onClose();
    modal.classList.remove('visible');
    modal.style.display = 'none';
  });

  // Re-enroll button
  modal.querySelector<HTMLButtonElement>('#settings-reenroll')?.addEventListener('click', () => {
    onReEnroll();
    // onReEnroll triggers app relaunch; panel will be destroyed anyway
  });

  // Backdrop click → close
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      onClose();
      modal.classList.remove('visible');
      modal.style.display = 'none';
    }
  });

  // ESC key → close
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      modal.classList.remove('visible');
      modal.style.display = 'none';
      document.removeEventListener('keydown', handleEsc);
    }
  };
  document.addEventListener('keydown', handleEsc);

  // Store cleanup function on element for caller
  (modal as any)._cleanup = () => document.removeEventListener('keydown', handleEsc);

  return modal;
}
