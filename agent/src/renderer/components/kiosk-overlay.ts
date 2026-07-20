/**
 * Kiosk overlay UI component — plain DOM, no external lib.
 * Built for the Arcade Agent electron renderer process.
 */

export interface KioskOverlayState {
  cafeName: string;
  sessionActive: boolean;
  remainingTime: string;
  callStaffEnabled: boolean;
}

/**
 * Encapsulates all kiosk overlay UI: top bug (wordmark + status pill),
 * hero cluster (brand, event banner, clock, timer, session indicator),
 * and bottom status rail.
 */
export class KioskOverlay {
  public readonly container: HTMLDivElement;
  private readonly bugEl: HTMLDivElement;
  private readonly statusPill: HTMLDivElement;
  private readonly centerEl: HTMLDivElement;
  private readonly cafeBrandEl: HTMLDivElement;
  private readonly clockEl: HTMLDivElement;
  private readonly timerEl: HTMLDivElement;
  private readonly sessionIndicator: HTMLDivElement;
  private readonly bannerEl: HTMLDivElement;
  private readonly railEl: HTMLDivElement;
  private clockInterval: ReturnType<typeof setInterval> | null = null;

  constructor(parent: HTMLElement) {
    this.container = document.createElement('div');
    this.container.className = 'kiosk-overlay';
    parent.appendChild(this.container);

    // Top bug: product wordmark + OPEN/LIVE status pill
    this.bugEl = document.createElement('div');
    this.bugEl.className = 'kiosk-bug';
    const wordmark = document.createElement('span');
    wordmark.className = 'cafe-wordmark';
    wordmark.textContent = 'ARCADE';
    this.statusPill = document.createElement('div');
    this.statusPill.className = 'status-pill';
    this.statusPill.innerHTML = '<span class="dot"></span><span class="label">OPEN</span>';
    this.bugEl.append(wordmark, this.statusPill);
    this.container.appendChild(this.bugEl);

    // Centered hero cluster
    this.centerEl = document.createElement('div');
    this.centerEl.className = 'kiosk-center';

    this.cafeBrandEl = document.createElement('div');
    this.cafeBrandEl.className = 'cafe-brand';
    this.centerEl.appendChild(this.cafeBrandEl);

    this.bannerEl = document.createElement('div');
    this.bannerEl.className = 'event-banner';
    this.bannerEl.style.display = 'none';
    this.centerEl.appendChild(this.bannerEl);

    this.clockEl = document.createElement('div');
    this.clockEl.className = 'clock';
    this.centerEl.appendChild(this.clockEl);

    this.timerEl = document.createElement('div');
    this.timerEl.className = 'timer-display';
    this.centerEl.appendChild(this.timerEl);

    this.sessionIndicator = document.createElement('div');
    this.sessionIndicator.className = 'session-indicator';
    this.sessionIndicator.textContent = '● Session in progress';
    this.centerEl.appendChild(this.sessionIndicator);

    this.container.appendChild(this.centerEl);

    // Bottom rail: status
    this.railEl = document.createElement('div');
    this.railEl.className = 'kiosk-rail';
    const railStatus = document.createElement('div');
    railStatus.className = 'kiosk-status';
    railStatus.innerHTML = '<span class="ok"></span><span>Online</span>';
    this.railEl.appendChild(railStatus);
    this.container.appendChild(this.railEl);
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

  /** Show/hide the session indicator and drive the bug status pill. */
  setSessionActive(active: boolean): void {
    const label = this.statusPill.querySelector('.label');
    if (active) {
      this.sessionIndicator.classList.add('active');
      this.statusPill.classList.add('live');
      if (label) label.textContent = 'LIVE';
    } else {
      this.sessionIndicator.classList.remove('active');
      this.statusPill.classList.remove('live');
      if (label) label.textContent = 'OPEN';
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

  /** Show the server-provided event banner, or hide it when empty/unset. */
  setEventBanner(text?: string): void {
    if (text && text.trim().length > 0) {
      this.bannerEl.textContent = text;
      this.bannerEl.style.display = '';
    } else {
      this.bannerEl.style.display = 'none';
    }
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
