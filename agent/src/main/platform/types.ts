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
   * Hide and destroy the kiosk overlay window, if it exists.
   *
   * After hiding, the kiosk overlay is completely destroyed. A subsequent call
   * to `showKioskOverlay` will create a fresh window.
   */
  hideKioskOverlay(): void;

  /**
   * Update the visible timer display on the kiosk overlay.
   *
   * Must be called after `showKioskOverlay`. No-op if the overlay is not visible.
   */
  updateTimer(timeString: string): void;

  /**
   * Announce a message on the kiosk overlay for a given duration (milliseconds).
   *
   * No-op if the overlay is not visible.
   */
  sendAnnouncement(text: string, durationMs: number): void;

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
