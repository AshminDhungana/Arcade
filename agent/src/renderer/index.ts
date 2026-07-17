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

/** Format elapsed seconds as HH:MM:SS (hours can exceed 99). */
function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
}

declare global {
  interface Window {
    electronAPI: {
      onOverlayContent: (callback: (data: OverlayData) => void) => void;
      onTimerUpdate: (callback: (timer: { elapsedSeconds: number }) => void) => void;
      onAnnouncement: (callback: (text: string, durationMs: number) => void) => void;
      onLowTimeWarning: (callback: (minutes: number) => void) => void;
      onSessionStatus: (callback: (active: boolean) => void) => void;
      callStaff: () => void;
      staffOverride: (pin: string) => void;
      openSettings: () => void;
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

  window.electronAPI.onTimerUpdate((timer) => {
    overlay.setTimer(formatElapsed(timer.elapsedSeconds));
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
          onSettings: () => window.electronAPI.openSettings(),
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
  // Branded cafe name/logo header (Task 9 — Epic 5.5)
  if (data.cafeName) {
    overlay.setCafeName(data.cafeName, data.cafeLogo);
  }
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
