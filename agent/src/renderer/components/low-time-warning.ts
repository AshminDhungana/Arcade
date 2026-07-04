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

  const closeBtn = modal.querySelector<HTMLButtonElement>('#low-time-close');
  closeBtn?.addEventListener('click', () => {
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
