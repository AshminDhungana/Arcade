/**
 * Low-time warning modal — pure DOM helper.
 *
 * Creates a modal element that displays a warning like
 * "⏰ 5 minutes remaining — please see staff to extend your session."
 * with an OK button to dismiss.
 */

export interface LowTimeWarningOptions {
  minutesRemaining: number;
  onDismiss?: () => void;
}

/** Format a duration in seconds as zero-padded "MM:SS" (pure, for tests). */
export function formatCountdown(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(safe / 60)).padStart(2, '0');
  const ss = String(safe % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

/**
 * Build and return the low-time warning modal element.
 * Callers must insert it into the DOM and remove it when done.
 */
export function createLowTimeModal(options: LowTimeWarningOptions): HTMLDivElement {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.style.display = 'flex';

  const minutesText = options.minutesRemaining === 1
    ? '1 minute remaining'
    : `${options.minutesRemaining} minutes remaining`;

  const countdownEl = document.createElement('div');
  countdownEl.className = 'low-time-countdown';

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-title">⏰ Time Running Low</div>
      <div class="modal-body">
        <p>${minutesText}.</p>
        <p>Please see staff to extend your session.</p>
      </div>
      <div class="modal-actions">
        <button class="modal-btn primary" id="low-time-close">OK</button>
      </div>
    </div>
  `;
  // Mount the live countdown beneath the body copy.
  modal.querySelector('.modal-content')?.appendChild(countdownEl);

  let remaining = options.minutesRemaining * 60;
  const renderCountdown = () => {
    countdownEl.textContent = `${formatCountdown(remaining)} remaining — please see staff`;
  };
  renderCountdown();
  const timer = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(timer);
      countdownEl.textContent = '00:00 remaining — please see staff';
      return;
    }
    renderCountdown();
  }, 1000);

  const closeBtn = modal.querySelector<HTMLButtonElement>('#low-time-close');
  closeBtn?.addEventListener('click', () => {
    clearInterval(timer);
    options.onDismiss?.();
    hideModal(modal);
  });

  return modal;
}

/** Show a modal element (assumes it's already in the DOM). */
export function showModal(el: HTMLDivElement): void {
  el.style.display = 'flex';
  // Force reflow so the opacity transition takes effect
  void el.offsetWidth;
  el.classList.add('visible');
}

/** Hide a modal element with an opacity transition. */
export function hideModal(el: HTMLDivElement): void {
  el.classList.remove('visible');
  setTimeout(() => {
    el.style.display = 'none';
  }, 300);
}
