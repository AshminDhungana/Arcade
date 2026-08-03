// agent/src/renderer/hud.ts

import { nextHudPhase, type HudPhase, type HudEvent } from './hud-state.js';
import { reveal, pulseTimer, countdown } from './motion.js';
import { createLowTimeModal, showModal, hideModal } from './components/low-time-warning.js';

let phase: HudPhase = 'ENDED';
let timerEl: HTMLDivElement | null = null;
let callBtn: HTMLButtonElement | null = null;
let railEl: HTMLDivElement | null = null;
let introTimerId: ReturnType<typeof setTimeout> | null = null;
let callStaffTimerId: ReturnType<typeof setTimeout> | null = null;
let urgentCountdownStop: (() => void) | null = null;
let lowTimeModal: HTMLDivElement | null = null;

const HOVER_ZONE = 0.12; // bottom-right hotzone size (fraction of viewport)
let pendingLowTimeMinutes = 5;

function showToast(message: string, durationMs = 3000): void {
  let toast = document.querySelector('.hud-toast') as HTMLDivElement;
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'hud-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.display = 'block';
  toast.style.opacity = '1';
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => { toast.style.display = 'none'; }, 300);
  }, durationMs);
}

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
  if (railEl) {
    railEl.style.display = 'flex';
  }
  if (callBtn) {
    callBtn.style.display = 'block';
    reveal(callBtn, 80);
  }
  // INTRO timer ~5s
  introTimerId = setTimeout(() => setPhase('AMBIENT', 'intro-timeout'), 5000);
  // Call Staff visible for 30s (hides rail and button)
  callStaffTimerId = setTimeout(() => { 
    if (railEl) railEl.style.display = 'none'; 
    if (callBtn) callBtn.style.display = 'none';
  }, 30000);
}

function hideAll(): void {
  if (timerEl) timerEl.style.display = 'none';
  if (railEl) railEl.style.display = 'none';
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
  if (railEl) {
    railEl.style.display = 'flex';
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

  // --- Add rail container matching kiosk overlay ---
  railEl = document.createElement('div');
  railEl.className = 'hud-rail';
  railEl.style.position = 'fixed';
  railEl.style.bottom = '4vh';
  railEl.style.left = '4vw';
  railEl.style.right = '4vw';
  railEl.style.display = 'none'; // hidden by default, shown by hot-zone
  railEl.style.alignItems = 'center';
  railEl.style.justifyContent = 'flex-end';
  railEl.style.pointerEvents = 'none';
  railEl.style.zIndex = '100';
  app.appendChild(railEl);

  callBtn = document.createElement('button');
  callBtn.className = 'call-staff-btn';
  callBtn.textContent = 'Call Staff';
  callBtn.style.display = 'none'; // button hidden inside rail initially
  callBtn.addEventListener('click', () => window.electronAPI.callStaff());
  railEl.appendChild(callBtn);

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

  // Listen for STAFF_ALERT_ACK from main process (sent when server confirms staff alert)
  window.electronAPI.onStaffAlertAck(() => {
    showToast('✓ Staff notified');
  });

  // Track hover state on the button for hover-extension
  let isHoveringButton = false;
  callBtn?.addEventListener('mouseenter', () => { isHoveringButton = true; });
  callBtn?.addEventListener('mouseleave', () => { isHoveringButton = false; });

  // Corner hot-zone (bottom-right 12%) → show rail for 5s with hover extension
  let hoverTimer: ReturnType<typeof setTimeout> | null = null;
  function scheduleHide() {
    if (hoverTimer) clearTimeout(hoverTimer);
    hoverTimer = setTimeout(checkAndHide, 5000);
  }
  function checkAndHide() {
    if (!isHoveringButton && railEl) {
      railEl.style.display = 'none';
      if (callBtn) callBtn.style.display = 'none';
    } else if (isHoveringButton) {
      hoverTimer = setTimeout(checkAndHide, 500); // Re-check while hovering
    }
  }
  window.addEventListener('mousemove', (e) => {
    if (e.clientX > innerWidth * (1 - HOVER_ZONE) && e.clientY > innerHeight * (1 - HOVER_ZONE)) {
      if (railEl && railEl.style.display === 'none' && phase !== 'ENDED') {
        railEl.style.display = 'flex';
        if (callBtn) {
          callBtn.style.display = 'block';
          reveal(callBtn, 80);
        }
        showToast('✓ Call Staff available');
        scheduleHide();
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

export { initHud, showToast };
