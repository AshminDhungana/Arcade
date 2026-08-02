/**
 * Renderer entry point for the kiosk overlay.
 *
 * Boots the DOM, starts the live clock, wires IPC listeners,
 * and handles the `Ctrl+Shift+O` staff-override shortcut.
 */

import { KioskOverlay } from './components/kiosk-overlay.js';
import { createLowTimeModal, showModal, hideModal } from './components/low-time-warning.js';
import { createStaffOverrideDialog } from './components/staff-override-dialog.js';
import { createSettingsPanel } from './components/settings-panel.js';
import type { OverlayData, ElectronAPI } from './types.js';

/** Format elapsed seconds as HH:MM:SS (hours can exceed 99). */
function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
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
  let hasOverrideCode = false;
  let currentConfig: OverlayData | null = null;

  window.electronAPI.onConfig((config) => {
    hasOverrideCode = config.hasOverrideCode;
  });

  window.electronAPI.onOverlayContent((data: OverlayData) => {
    currentConfig = data;
    overlay.setCafeName(data.cafeName, data.cafeLogo);
    overlay.setEventBanner(data.eventBanner);
    overlay.setSessionActive(data.sessionActive);
    if (data.remainingTime) {
      overlay.setTimer(data.remainingTime);
    }
    if (typeof data.overrideCodeConfigured === 'boolean') {
      hasOverrideCode = data.overrideCodeConfigured;
    }
  });

  window.electronAPI.onTimerUpdate(({ elapsedSeconds }) => {
    overlay.setTimer(formatElapsed(elapsedSeconds));
  });

  window.electronAPI.onAnnouncement((text, durationMs) => {
    overlay.showAnnouncement(text, durationMs);
  });

  window.electronAPI.onLowTimeWarning((minutes) => {
    const modal = createLowTimeModal({
      minutesRemaining: minutes,
      onDismiss: () => hideModal(modal),
    });
    showModal(modal);
  });

  window.electronAPI.onSessionStatus((active) => {
    overlay.setSessionActive(active);
  });

  // --- Staff override (Ctrl+Shift+O) ---
  let overrideDialog: ReturnType<typeof createStaffOverrideDialog> | null = null;

  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'O') {
      e.preventDefault();
      if (!hasOverrideCode) {
        overlay.showAnnouncement('Staff override not configured', 3000);
        return;
      }
      if (!overrideDialog) {
        overrideDialog = createStaffOverrideDialog({
          onOverride: (pin: string) => {
            window.electronAPI.staffOverride(pin);
            overrideDialog = null;
          },
          onCancel: () => {
            overrideDialog = null;
          },
        });
      }
      showModal(overrideDialog);
    }
  });

  // --- Call staff button ---
  overlay.onCallStaff(() => {
    window.electronAPI.callStaff();
    overlay.showCallStaffConfirmation();
  });

  // --- Settings button → in-overlay panel ---
  overlay.onSettingsPanel(() => {
    if (!currentConfig) {
      overlay.showAnnouncement('Settings unavailable', 2000);
      return;
    }
    const panel = createSettingsPanel({
      config: {
        serverUrl: currentConfig.serverUrl || 'Unknown',
        seatId: currentConfig.seatId || 'Unknown',
        agentSecret: currentConfig.agentSecret || '',
      },
      onReEnroll: () => {
        window.electronAPI.openSettings(); // triggers re-enroll flow
      },
      onClose: () => {
        hideModal(panel);
        (panel as any)._cleanup?.();
      },
    });
    showModal(panel);
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  initKiosk();
});

export {};
