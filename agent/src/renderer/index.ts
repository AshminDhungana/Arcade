/**
 * Renderer entry point for the kiosk overlay.
 *
 * Boots the DOM, starts the live clock, wires IPC listeners,
 * and handles the `Ctrl+Shift+O` staff-override shortcut.
 */

import { KioskOverlay } from './components/kiosk-overlay.js';
import { createLowTimeModal, showModal, hideModal } from './components/low-time-warning.js';
import { createStaffOverrideDialog } from './components/staff-override-dialog.js';
import type { OverlayData } from './preload.js';

declare global {
  interface Window {
    electronAPI: {
      onOverlayContent: (callback: (data: OverlayData) => void) => void;
      onTimerUpdate: (callback: (timeString: string) => void) => void;
      onAnnouncement: (callback: (text: string, durationMs: number) => void) => void;
      onLowTimeWarning: (callback: (minutes: number) => void) => void;
      onSessionStatus: (callback: (active: boolean) => void) => void;
      callStaff: () => void;
      staffOverride: (pin: string) => void;
    };
  }
}

// ---------------------------------------------------------------------------
// Initialise the kiosk overlay
// ---------------------------------------------------------------------------

function initKiosk(): void {
  const app = document.getElementById('app');
  if (!app) {
    console.error('[Renderer] #app container not found');
    return;
  }

  // --- Core overlay ---
  const overlay = new KioskOverlay(app);
  overlay.startClock();

  // --- IPC Listeners from preload ---
  window.electronAPI.onOverlayContent((data) => {
    updateOverlay(overlay, data);
  });

  window.electronAPI.onTimerUpdate((timeString) => {
    overlay.setTimer(timeString);
  });

  window.electronAPI.onSessionStatus((active) => {
    overlay.setSessionActive(active);
  });

  // --- Announcement banner ---
  const announcementEl = document.createElement('div');
  announcementEl.className = 'announcement-banner';
  document.body.appendChild(announcementEl);

  window.electronAPI.onAnnouncement((text, durationMs) => {
    showAnnouncement(announcementEl, text, durationMs);
  });

  // --- Low-time warning modal ---
  let lowTimeModal: HTMLDivElement | null = null;
  window.electronAPI.onLowTimeWarning((minutes) => {
    if (!lowTimeModal) {
      lowTimeModal = createLowTimeModal({
        minutesRemaining: minutes,
        onDismiss: () => {
          if (lowTimeModal) {
            hideModal(lowTimeModal);
          }
        },
      });
      document.body.appendChild(lowTimeModal);
    }
    showModal(lowTimeModal);
  });

  // --- Staff override — Ctrl+Shift+O ---
  let overrideDialog: HTMLDivElement | null = null;
  document.addEventListener('keydown', (event) => {
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'o') {
      event.preventDefault();
      if (!overrideDialog) {
        overrideDialog = createStaffOverrideDialog({
          onOverride: (pin) => {
            window.electronAPI.staffOverride(pin);
          },
          onCancel: () => {
            /* dialog will clean itself up via its internal handler */
          },
        });
        document.body.appendChild(overrideDialog);
      }
      showModal(overrideDialog);
    }
  });

  // --- Call Staff button ---
  const callStaffBtn = document.createElement('button');
  callStaffBtn.className = 'call-staff-btn';
  callStaffBtn.textContent = 'Call Staff';
  callStaffBtn.addEventListener('click', () => {
    window.electronAPI.callStaff();
  });
  overlay.container.appendChild(callStaffBtn);

  // --- Initial state ---
  const initialData: OverlayData = {
    cafeName: 'Arcade',
    sessionActive: false,
    callStaffEnabled: true,
    announcements: [],
  };
  updateOverlay(overlay, initialData);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function updateOverlay(overlay: KioskOverlay, data: OverlayData): void {
  // Session status drives the indicator
  if (data.sessionActive) {
    overlay.setSessionActive(true);
  } else {
    overlay.setSessionActive(false);
  }
}

function showAnnouncement(el: HTMLDivElement, text: string, durationMs: number): void {
  el.textContent = text;
  el.classList.add('visible');
  setTimeout(() => {
    el.classList.remove('visible');
  }, durationMs);
}

// Boot on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initKiosk);
} else {
  initKiosk();
}
