// agent/src/renderer/hud.ts

import { nextHudPhase, type HudPhase, type HudEvent } from './hud-state.js';
import { reveal, pulseTimer, countdown } from './motion.js';
import { createLowTimeModal, showModal, hideModal } from './components/low-time-warning.js';

let phase: HudPhase = 'ENDED';
let timerEl: HTMLDivElement | null = null;
let callBtn: HTMLButtonElement | null = null;
let introTimerId: ReturnType<typeof setTimeout> | null = null;
let callStaffTimerId: ReturnType<typeof setTimeout> | null = null;
let urgentCountdownStop: (() => void) | null = null;
let lowTimeModal: HTMLDivElement | null = null;

function setPhase(next: HudPhase, event: HudEvent): void {
  phase = nextHudPhase(phase, event);
  applyPhase();
}

function applyPhase(): void {
  switch (phase) {
    case 'INTRO':
      showIntro();
      break;
    case 'AMBIENT':
      hideAll();
      break;
    case 'URGENT':
      showUrgent();
      break;
    case 'ENDED':
      hideAll();
      break;
  }
}

function showIntro(): void {
  if (timerEl) {
    timerEl.style.display = 'block';
    reveal(timerEl);
  }
  if (callBtn) {
    callBtn.style.display = 'block';
    reveal(callBtn, 80);
  }
  // INTRO timer ~5s
  introTimerId = setTimeout(() => setPhase('AMBIENT', 'intro-timeout'), 5000);
  // Call Staff visible for 30s
  callStaffTimerId = setTimeout(() => { if (callBtn) callBtn.style.display = 'none'; }, 30000);
}

function hideAll(): void {
  if (timerEl) timerEl.style.display = 'none';
  if (callBtn) callBtn.style.display = 'none';
  if (introTimerId) clearTimeout(introTimerId);
  if (callStaffTimerId) clearTimeout(callStaffTimerId);
  if (urgentCountdownStop) urgentCountdownStop();
  urgentCountdownStop = null;
  if (lowTimeModal) { hideModal(lowTimeModal); lowTimeModal = null; }
}

function showUrgent(): void {
  if (timerEl) {
    timerEl.style.display = 'block';
    reveal(timerEl);
    // local countdown from server's remaining seconds (placeholder 300s)
    urgentCountdownStop = countdown(300, (rem) => {
      timerEl!.textContent = formatMMSS(rem);
      pulseTimer(timerEl!);
    }, () => {
      setPhase('ENDED', 'session-end');
    });
  }
  if (callBtn) {
    callBtn.style.display = 'block';
    reveal(callBtn, 80);
  }
  // low-time modal
  if (!lowTimeModal) {
    lowTimeModal = createLowTimeModal({
      minutesRemaining: 5,
      onDismiss: () => { if (lowTimeModal) { hideModal(lowTimeModal); lowTimeModal = null; } },
    });
    document.body.appendChild(lowTimeModal);
  }
  showModal(lowTimeModal);
}

function formatMMSS(total: number): string {
  const m = Math.floor(total / 60).toString().padStart(2, '0');
  const s = (total % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function initHud(): void {
  const app = document.getElementById('app')!;
  app.style.pointerEvents = 'none'; // click-through except button

  timerEl = document.createElement('div');
  timerEl.className = 'hud-timer';
  timerEl.style.display = 'none';
  app.appendChild(timerEl);

  callBtn = document.createElement('button');
  callBtn.className = 'call-staff-btn';
  callBtn.textContent = 'Call Staff';
  callBtn.style.display = 'none';
  callBtn.style.pointerEvents = 'auto'; // button is clickable
  callBtn.addEventListener('click', () => window.electronAPI.callStaff());
  app.appendChild(callBtn);

  // Preload low-time modal CSS via component (already included)

  // Session start → INTRO
  window.electronAPI.onTimerUpdate((tick: { elapsedSeconds: number }) => {
    if (phase === 'INTRO') {
      timerEl!.textContent = formatMMSS(tick.elapsedSeconds);
    }
  });

  window.electronAPI.onLowTimeWarning((minutes: number) => {
    setPhase('URGENT', 'low-time');
  });

  window.electronAPI.onSessionStatus((status: string) => {
    if (status === 'active') setPhase('INTRO', 'session-start');
    else if (status === 'ended') setPhase('ENDED', 'session-end');
  });

  window.electronAPI.onAnnouncement((text: string, durationMs: number) => {
    const el = document.createElement('div');
    el.className = 'announcement-banner';
    el.textContent = text;
    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add('visible'));
    setTimeout(() => { el.classList.remove('visible'); el.remove(); }, durationMs);
  });

  // Corner hot-zone (bottom-right 64x64) → show Call Staff for 10s
  let hoverTimer: ReturnType<typeof setTimeout> | null = null;
  window.addEventListener('mousemove', (e) => {
    if (e.clientX > innerWidth - 64 && e.clientY > innerHeight - 64) {
      if (callBtn && callBtn.style.display === 'none' && phase !== 'ENDED') {
        callBtn.style.display = 'block';
        reveal(callBtn, 80);
        if (hoverTimer) clearTimeout(hoverTimer);
        hoverTimer = setTimeout(() => { if (callBtn) callBtn.style.display = 'none'; }, 10000);
      }
    }
  });
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHud);
  } else {
    initHud();
  }
}

export { initHud };
