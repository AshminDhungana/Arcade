/**
 * Renderer entry point for the kiosk overlay.
 *
 * Boots the DOM, starts the live clock, wires IPC listeners,
 * and handles the `Ctrl+Shift+O` staff-override shortcut.
 */

import { KioskOverlay } from './components/kiosk-overlay.js';
import { createLowTimeModal, showModal, hideModal } from './components/low-time-warning.js';
import { createStaffOverrideDialog } from './components/staff-override-dialog.js';
import { createSettingsPinDialog } from './components/settings-pin-dialog.js';
import { createSettingsPanel } from './components/settings-panel.js';
import type { OverlayData } from './types.js';

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

  // NEW: Set fallback name immediately on init
  overlay.setArcadeName('Arcade');

  overlay.startClock();

  // --- IPC Listeners from preload ---
  let hasOverrideCode = false;
  let currentConfig: OverlayData | null = null;
  let minimalMode = false;
  let hotspotHovered = false;
  let modalOpen = false;

  /**
   * Recompute OS-level click-through for the kiosk window.
   * Click-through is active only in minimal mode when no hot-zone hover is
   * holding the Call Staff button and no modal is open (PIN dialogs need
   * real clicks). The desktop below stays usable whenever it is active.
   */
  const syncClickThrough = (): void => {
    window.electronAPI.setClickThrough(minimalMode && !hotspotHovered && !modalOpen);
  };

  // Track modal visibility so PIN dialogs stay clickable in minimal mode.
  const modalObserver = new MutationObserver(() => {
    const open = document.querySelector('.modal-overlay.visible') !== null;
    if (open !== modalOpen) {
      modalOpen = open;
      syncClickThrough();
    }
  });
  modalObserver.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class'],
  });

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
          onOverride: async (pin: string) => {
            const result = await window.electronAPI.staffOverride(pin);
            if (result) {
              hideModal(overrideDialog!);
              overrideDialog = null;
            } else {
              overrideDialog?._showError?.();
            }
          },
          onCancel: () => {
            hideModal(overrideDialog!);
            overrideDialog = null;
          },
          onSettings: () => {
            if (!currentConfig) {
              overlay.showAnnouncement('Settings unavailable', 2000);
              return;
            }
            const serverUrl = currentConfig.serverUrl ?? '';
            const seatId = currentConfig.seatId ?? '';
            const agentSecret = currentConfig.agentSecret ?? '';
            // Show Settings PIN dialog
            const pinDialog = createSettingsPinDialog({
              onVerify: async (pin: string) => {
                const success = await window.electronAPI.verifySettingsPin(pin);
                return success;
              },
              onCancel: () => {
                // PIN dialog cancelled, return to override dialog
              },
              onSuccess: () => {
                // Create and show Settings panel
                const settingsPanel = createSettingsPanel({
                  config: {
                    serverUrl,
                    seatId,
                    agentSecret,
                  },
                  onReEnroll: () => {
                    window.electronAPI.enroll('');
                  },
                  onClose: () => {
                    // Settings panel closed, return to kiosk overlay
                  },
                });
                showModal(settingsPanel);
              },
            });
            showModal(pinDialog);
          },
        });
      }
      showModal(overrideDialog);
    }
  });

  // --- Call staff button ---
  overlay.onCallStaff(() => {
    window.electronAPI.callStaff();
  });

  // --- Staff alert ACK (from server) ---
  window.electronAPI.onStaffAlertAck?.(() => {
    overlay.showCallStaffConfirmation();
  });

  // --- Minimal mode toggle ---
  window.electronAPI.onSetMinimal((enabled) => {
    minimalMode = enabled;
    overlay.setMinimalMode(enabled);
    if (!enabled) {
      hotspotHovered = false;
    }
    syncClickThrough();
  });

  // --- Right-edge hot zone (Call Staff button) toggles click-through ---
  overlay.onHotspotHover((active) => {
    hotspotHovered = active;
    syncClickThrough();
  });

  // Main process polls the OS cursor (Electron's forwarded mouse events are
  // unreliable on Windows) and reports whether the hot zone is hovered.
  window.electronAPI.onHotspot((active) => {
    overlay.setHotspotActive(active);
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  initKiosk();
});

export {};
