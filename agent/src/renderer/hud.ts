/**
 * HUD renderer — transparent, always-on-top overlay shown over the live
 * game during a session (Epic 5.5). Carries the session ticker,
 * low-time modal, staff popup, and an interactive Call Staff button.
 *
 * Click-through is handled at the window level (setIgnoreMouseEvents with
 * { forward: true }) plus CSS pointer-events, so no IPC is needed here.
 */

import { createLowTimeModal, showModal, hideModal } from './components/low-time-warning.js';

/** Format elapsed seconds as HH:MM:SS (hours can exceed 99). */
function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
}

export function initHud(): void {
  const app = document.getElementById('app');
  if (!app) return;

  const topBar = document.createElement('div');
  topBar.className = 'hud-top-bar';

  const brand = document.createElement('div');
  brand.className = 'cafe-brand';
  brand.textContent = 'Arcade';

  const indicator = document.createElement('div');
  indicator.className = 'hud-session-indicator';
  indicator.textContent = '● Session in progress';

  topBar.append(brand, indicator);

  const timer = document.createElement('div');
  timer.className = 'hud-timer';

  const callBtn = document.createElement('button');
  callBtn.className = 'call-staff-btn';
  callBtn.textContent = 'Call Staff';
  callBtn.addEventListener('click', () => window.electronAPI.callStaff());

  app.append(topBar, timer, callBtn);

  window.electronAPI.onOverlayContent((data) => {
    brand.textContent = data.cafeName;
    indicator.style.display = data.sessionActive ? 'block' : 'none';
  });

  window.electronAPI.onTimerUpdate((tick) => {
    timer.textContent = formatElapsed(tick.elapsedSeconds);
  });

  const announcementEl = document.createElement('div');
  announcementEl.className = 'announcement-banner';
  document.body.appendChild(announcementEl);
  window.electronAPI.onAnnouncement((text, durationMs) => {
    announcementEl.textContent = text;
    announcementEl.classList.add('visible');
    setTimeout(() => announcementEl.classList.remove('visible'), durationMs);
  });

  let lowTimeModal: HTMLDivElement | null = null;
  window.electronAPI.onLowTimeWarning((minutes) => {
    if (!lowTimeModal) {
      lowTimeModal = createLowTimeModal({
        minutesRemaining: minutes,
        onDismiss: () => lowTimeModal && hideModal(lowTimeModal),
      });
      document.body.appendChild(lowTimeModal);
    }
    showModal(lowTimeModal);
  });
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHud);
  } else {
    initHud();
  }
}
