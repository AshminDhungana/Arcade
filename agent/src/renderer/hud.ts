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

const HOVER_ZONE = 0.12; // bottom-right hotzone size (fraction of viewport)
let pendingLowTimeMinutes = 5;

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
      hideTimerOnly();
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
  // Clear any existing timers to prevent stacking on repeat calls (M3)
  if (introTimerId) clearTimeout(introTimerId);
  if (callStaffTimerId) clearTimeout(callStaffTimerId);

  if (timerEl) {
    timerEl.style.display = 'block';
    reveal(timerEl);
    timerEl.textContent = formatElapsed(0);
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

function hideTimerOnly(): void {
  if (timerEl) timerEl.style.display = 'none';
  if (introTimerId) clearTimeout(introTimerId);
}

function showUrgent(): void {
  if (timerEl) {
    timerEl.style.display = 'block';
    reveal(timerEl);
    // Clear any existing countdown to prevent interval leak (I2)
    if (urgentCountdownStop) {
      urgentCountdownStop();
      urgentCountdownStop = null;
    }
    // local countdown from server's remaining seconds
    urgentCountdownStop = countdown(pendingLowTimeMinutes * 60, (rem) => {
      timerEl!.textContent = formatMMSS(rem);
      pulseTimer(timerEl!);
    });
  }
  if (callBtn) {
    callBtn.style.display = 'block';
    reveal(callBtn, 80);
  }
  // low-time modal
  if (!lowTimeModal) {
    lowTimeModal = createLowTimeModal({
      minutesRemaining: pendingLowTimeMinutes,
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

function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
}

function initHud(): void {
  const app = document.getElementById('app')!;

  timerEl = document.createElement('div');
  timerEl.className = 'hud-timer';
  timerEl.style.display = 'none';
  app.appendChild(timerEl);

  callBtn = document.createElement('button');
  callBtn.className = 'call-staff-btn';
  callBtn.textContent = 'Call Staff';
  callBtn.style.display = 'none';
  callBtn.addEventListener('click', () => window.electronAPI.callStaff());
  app.appendChild(callBtn);

  // Preload low-time modal CSS via component (already included)

  // Session start → INTRO
  window.electronAPI.onTimerUpdate((tick: { elapsedSeconds: number }) => {
    if (phase === 'INTRO') {
      timerEl!.textContent = formatElapsed(tick.elapsedSeconds);
    }
  });

  window.electronAPI.onLowTimeWarning((minutes: number) => {
    pendingLowTimeMinutes = minutes;
    setPhase('URGENT', 'low-time');
  });

  window.electronAPI.onSessionStatus((status: boolean | string) => {
    // Preload sends boolean (data.active), but test mocks may send string 'active'/'ended'.
    // Treat truthy as active, falsy as ended.
    const active = typeof status === 'boolean' ? status : status === 'active';
    setPhase(active ? 'INTRO' : 'ENDED', active ? 'session-start' : 'session-end');
  });

  window.electronAPI.onAnnouncement((text: string, durationMs: number) => {
    const el = document.createElement('div');
    el.className = 'announcement-banner';
    el.textContent = text;
    el.style.pointerEvents = 'none';
    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add('visible'));
    setTimeout(() => { el.classList.remove('visible'); el.remove(); }, durationMs);
  });

  // Corner hot-zone (bottom-right 64x64) → show Call Staff for 10s
  let hoverTimer: ReturnType<typeof setTimeout> | null = null;
  window.addEventListener('mousemove', (e) => {
    if (e.clientX > innerWidth * (1 - HOVER_ZONE) && e.clientY > innerHeight * (1 - HOVER_ZONE)) {
      if (callBtn && callBtn.style.display === 'none' && phase !== 'ENDED') {
        callBtn.style.display = 'block';
        reveal(callBtn, 80);
        if (hoverTimer) clearTimeout(hoverTimer);
        hoverTimer = setTimeout(() => { if (callBtn) callBtn.style.display = 'none'; }, 10000);
      }
    }
  });

  // C1 fix: HUD window is created only when a session starts (showHud() called from hideKioskOverlay()).
  // Therefore "HUD window created" == "session start". Auto-trigger INTRO phase.
  setPhase('INTRO', 'session-start');
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHud);
  } else {
    initHud();
  }
}

export { initHud };
