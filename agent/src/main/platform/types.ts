/**
 * Content displayed on the kiosk overlay when shown.
 */
export interface OverlayContent {
  /** Optional base64-encoded cafe logo or absolute file path. */
  cafeLogo?: string;

  /** Displayed as the header / cafe name. */
  cafeName: string;

  /** Active announcements (e.g. "Tournament at 6 PM"). */
  announcements: string[];

  /** Whether the "Call Staff" button is enabled. */
  callStaffEnabled: boolean;

  /** True if a session is currently active. */
  sessionActive: boolean;

  /** Remaining time as "HH:MM:SS" or "Unlimited" when absent. */
  remainingTime?: string;

  /** Whether to flash the low-time warning indicator. */
  lowTimeWarning?: boolean;

  /** Optional event/tournament banner shown on the kiosk when set by the server. */
  eventBanner?: string;

  /** Whether the staff override code is configured (shows Ctrl+Shift+O dialog). */
  overrideCodeConfigured?: boolean;

  /** Server WebSocket URL (for settings panel). */
  serverUrl?: string;

  /** Seat ID (for settings panel). */
  seatId?: string;

  /** Agent secret (masked in settings panel). */
  agentSecret?: string;
}

/**
 * Hardware / OS information returned by `getSystemInfo()`.
 */
export interface SystemInfo {
  /** CPU model name (e.g. "Intel(R) Core(TM) i7-9700K"). */
  cpuModel: string;

  /** Number of logical CPU cores. */
  cpuCores: number;

  /** Total system memory in gigabytes (rounded down). */
  totalMemoryGB: number;

  /** Total disk space in gigabytes (rounded down). */
  totalDiskGB: number;

  /** Operating system name (e.g. "Windows_NT"). */
  osName: string;

  /** OS version string (e.g. "10.0.22631"). */
  osVersion: string;

  /** Machine hostname. */
  hostname: string;
}

/**
 * Supported platform identifier for the factory.
 */
export type PlatformName = 'win32' | 'darwin' | 'linux';

/**
 * Abstraction over all platform-specific operations.
 *
 * Implementations manage an internal `BrowserWindow` for the kiosk overlay
 * and provide OS-specific equivalents for screenshot capture, system
 * commands and auto-start registration.
 */
export interface IPlatformService {
  /**
   * Show (or create) the kiosk overlay window with the given content.
   *
   * Creates a new `BrowserWindow` with `kiosk: true`, `alwaysOnTop: true`,
   * `frame: false`, `closable: false`, `devTools: false`.
   *
   * Keyboard shortcuts (Alt+F4, F12, Ctrl+P, etc.) are intercepted and discarded
   * in the `before-input-event` handler.
   */
  showKioskOverlay(content: OverlayContent): void;

  /**
   * Hide the kiosk overlay window (switch to minimal mode), if it exists.
   *
   * The kiosk window stays visible but enters minimal mode (transparent,
   * click-through except for hot corner trigger zone and Call Staff button).
   * A subsequent call to `showKioskOverlay` will restore full overlay mode.
   */
  hideKioskOverlay(): void;

  /**
   * Show the low-time warning in the kiosk overlay window.
   */
  showLowTimeWarning(minutes: number): void;

  /**
   * Update the visible timer display on the kiosk overlay with the elapsed
   * session time in seconds.
   *
   * `elapsedSeconds` is wall-clock seconds since session start (agent-local;
   * survives LAN drops). Epic 6.5.4 will extend this to include
   * `assignedEndAt`/`remainingSeconds` without changing this call site.
   *
   * Must be called after `showKioskOverlay`. No-op if the window is not visible.
   */
  updateTimer(timer: { elapsedSeconds: number }): void;

  /**
   * Announce a message on the kiosk overlay for a given duration (milliseconds).
   *
   * No-op if the window is not visible.
   */
  sendAnnouncement(text: string, durationMs: number): void;

  /** Return whether the kiosk overlay is currently visible. */
  isKioskVisible(): boolean;

  /** Send agent config to the kiosk overlay renderer. */
  sendConfigToOverlay(config: { hasOverrideCode: boolean }): void;

  /**
   * Send a message to the kiosk overlay window.
   * Used for events that should reach the overlay.
   */
  sendToOverlayAndHud(channel: string, data?: unknown): void;

  /** Restart the PC immediately. */
  restartPC(): Promise<void>;

  /** Shut down the PC immediately. */
  shutdownPC(): Promise<void>;

  /**
   * Capture a screenshot of the primary display.
   *
   * Uses `desktopCapturer.getSources({ types: ['screen'] })` and resizes
   * the resulting image to 1280x720 max using `sharp` with 80% JPEG quality.
   */
  captureScreenshot(): Promise<Buffer>;

  /** Register the agent to start automatically on system boot. */
  enableAutoStart(): Promise<void>;

  /** Remove the auto-start registration. */
  disableAutoStart(): Promise<void>;

  /** Return hardware and OS metadata for the REGISTER payload. */
  getSystemInfo(): Promise<SystemInfo>;
}
