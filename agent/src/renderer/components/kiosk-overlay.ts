/**
 * Kiosk overlay UI component — plain DOM, no external lib.
 * Built for the Arcarde Agent electron renderer process.
 */

export interface KioskOverlayState {
  cafeName: string;
  sessionActive: boolean;
  remainingTime: string;
  callStaffEnabled: boolean;
}

/**
 * Encapsulates all kiosk overlay UI: live clock, session indicator,
 * timer display, and "Call Staff" button.
 */
export class KioskOverlay {
  public readonly container: HTMLDivElement;
  private readonly cafeBrandEl: HTMLDivElement;
  private readonly clockEl: HTMLDivElement;
  private readonly timerEl: HTMLDivElement;
  private readonly sessionIndicator: HTMLDivElement;
  private clockInterval: ReturnType<typeof setInterval> | null = null;

  constructor(parent: HTMLElement) {
    this.container = document.createElement('div');
    this.container.className = 'kiosk-overlay';
    parent.appendChild(this.container);

    this.cafeBrandEl = document.createElement('div');
    this.cafeBrandEl.className = 'cafe-brand';
    this.container.appendChild(this.cafeBrandEl);

    this.clockEl = document.createElement('div');
    this.clockEl.className = 'clock';
    this.container.appendChild(this.clockEl);

    this.timerEl = document.createElement('div');
    this.timerEl.className = 'timer-display';
    this.container.appendChild(this.timerEl);

    this.sessionIndicator = document.createElement('div');
    this.sessionIndicator.className = 'session-indicator';
    this.sessionIndicator.textContent = '● Session in progress';
    this.container.appendChild(this.sessionIndicator);
  }

  /** Start the live clock (updates every second). */
  startClock(): void {
    this.updateClock();
    this.clockInterval = setInterval(() => this.updateClock(), 1000);
  }

  /** Stop the live clock. */
  stopClock(): void {
    if (this.clockInterval !== null) {
      clearInterval(this.clockInterval);
      this.clockInterval = null;
    }
  }

  /** Update the visible timer string (e.g., "00:05:32"). */
  setTimer(timeString = ''): void {
    this.timerEl.textContent = timeString;
  }

  /** Show or hide the "Session in progress" indicator. */
  setSessionActive(active: boolean): void {
    if (active) {
      this.sessionIndicator.classList.add('active');
    } else {
      this.sessionIndicator.classList.remove('active');
      this.timerEl.textContent = '';
    }
  }

  /** Render the branded cafe name/logo header. */
  setCafeName(name: string, logo?: string): void {
    this.cafeBrandEl.replaceChildren();
    if (logo) {
      const img = document.createElement('img');
      img.src = logo;
      img.className = 'cafe-logo';
      img.alt = name;
      this.cafeBrandEl.appendChild(img);
    }
    const span = document.createElement('span');
    span.textContent = name;
    this.cafeBrandEl.appendChild(span);
  }

  /** Return whether clock is running. */
  isClockRunning(): boolean {
    return this.clockInterval !== null;
  }

  /** Tear down the component. */
  destroy(): void {
    this.stopClock();
    if (this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
  }

  private updateClock(): void {
    const now = new Date();
    this.clockEl.textContent = now.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  }
}
