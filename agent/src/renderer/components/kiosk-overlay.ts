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
  private readonly triggerZone: HTMLDivElement;
  private readonly callStaffBtn: HTMLButtonElement;
  private clockInterval: ReturnType<typeof setInterval> | null = null;
  private buttonVisible = false;
  private hideTimer: ReturnType<typeof setTimeout> | null = null;
  private isMouseOverButton = false;

  // NEW: Fallback name (default "Arcade")
  private arcadeName = 'Arcade';
  // NEW: Track server-provided cafe name
  private currentCafeName = '';

  constructor(parent: HTMLElement) {
    this.container = document.createElement('div');
    this.container.className = 'kiosk-overlay';
    parent.appendChild(this.container);

    // Hot-corner trigger zone
    this.triggerZone = document.createElement('div');
    this.triggerZone.className = 'kiosk-trigger-zone';
    this.container.appendChild(this.triggerZone);

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
    // Initialize with fallback name
    const span = document.createElement('span');
    span.textContent = this.arcadeName;
    this.cafeBrandEl.appendChild(span);
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

    // Bottom rail: status + buttons
    this.railEl = document.createElement('div');
    this.railEl.className = 'kiosk-rail';
    const railStatus = document.createElement('div');
    railStatus.className = 'kiosk-status';
    railStatus.innerHTML = '<span class="ok"></span><span>Online</span>';
    this.railEl.appendChild(railStatus);

    const callStaffBtn = document.createElement('button');
    callStaffBtn.className = 'kiosk-btn primary';
    callStaffBtn.textContent = 'Call Staff';
    callStaffBtn.addEventListener('click', () => {
      this.callStaffCb?.();
      this.showCallStaffConfirmation();
      this.hideButton();
    });
    this.callStaffBtn = callStaffBtn;
    this.railEl.appendChild(callStaffBtn);

    this.container.appendChild(this.railEl);

    // Event listeners for hot-corner trigger
    this.triggerZone.addEventListener('mouseenter', () => this.showButton());
    this.triggerZone.addEventListener('mouseleave', () => this.scheduleHide());
    this.callStaffBtn.addEventListener('mouseenter', () => {
      this.isMouseOverButton = true;
      this.clearHideTimer();
    });
    this.callStaffBtn.addEventListener('mouseleave', () => {
      this.isMouseOverButton = false;
      this.scheduleHide();
    });
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
    this.currentCafeName = (name || '').trim();
    this.cafeBrandEl.replaceChildren();
    if (logo) {
      const img = document.createElement('img');
      img.src = logo;
      img.className = 'cafe-logo';
      img.alt = this.currentCafeName || this.arcadeName;
      this.cafeBrandEl.appendChild(img);
    }
    const span = document.createElement('span');
    span.textContent = this.currentCafeName || this.arcadeName;
    this.cafeBrandEl.appendChild(span);
  }

  /** NEW: Set the fallback name (default 'Arcade'). */
  setArcadeName(name: string): void {
    this.arcadeName = name || 'Arcade';
    // If no server name has been set, update display immediately
    if (!this.currentCafeName) {
      this.cafeBrandEl.replaceChildren();
      const span = document.createElement('span');
      span.textContent = this.arcadeName;
      this.cafeBrandEl.appendChild(span);
    }
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

  /** Show a temporary announcement toast. */
  showAnnouncement(text: string, durationMs = 3000): void {
    let toast = this.container.querySelector('.kiosk-toast') as HTMLDivElement;
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'kiosk-toast';
      this.container.appendChild(toast);
    }
    toast.textContent = text;
    toast.style.display = 'block';
    setTimeout(() => {
      toast.style.display = 'none';
    }, durationMs);
  }

  /** Show a brief confirmation that staff was notified. */
  showCallStaffConfirmation(): void {
    this.showAnnouncement('✓ Staff notified', 3000);
  }

  private showButton(): void {
    this.buttonVisible = true;
    this.callStaffBtn.classList.add('visible');
    this.clearHideTimer();
  }

  private hideButton(): void {
    this.buttonVisible = false;
    this.callStaffBtn.classList.remove('visible');
  }

  private scheduleHide(): void {
    if (this.isMouseOverButton) return;
    this.clearHideTimer();
    this.hideTimer = setTimeout(() => this.hideButton(), 3000);
  }

  private clearHideTimer(): void {
    if (this.hideTimer !== null) {
      clearTimeout(this.hideTimer);
      this.hideTimer = null;
    }
  }

  /** Callback for call-staff button. */
  onCallStaff(cb: () => void): void {
    this.callStaffCb = cb;
  }

  /** Tear down the component. */
  destroy(): void {
    this.stopClock();
    this.clearHideTimer();
    if (this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
  }

  private callStaffCb: (() => void) | null = null;

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
