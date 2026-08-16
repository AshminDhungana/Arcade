import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
// Default import + destructure: under the Electron runtime this yields the
// real API object; under plain Node (smoke test) the CJS shim loads without
// a named-export SyntaxError, and the bindings are never used.
import electron from 'electron';
import type { BrowserWindow as BrowserWindowType } from 'electron';
const { BrowserWindow, desktopCapturer, screen, powerMonitor } = electron;
import { exec } from 'child_process';
import { promisify } from 'util';
import sharp from 'sharp';
import si from 'systeminformation';
import os from 'os';
import type { IPlatformService, OverlayContent, SystemInfo } from './types.js';
import { isTestMode } from './safety.js';

const execAsync = promisify(exec);

const AUTO_START_KEY = 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run';
const APP_NAME = 'ArcadeAgent';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BLOCKED_SHORTCUTS = [
  'Alt+F4',
  'Alt+Shift+I',
  'Control+Shift+I',
  'Control+P',
  'F12',
  'F11',
  'Escape',
];

export class WindowsPlatformService implements IPlatformService {
  private kioskWindow: BrowserWindowType | null = null;
  private sessionActive = false;
  private overrideCodeConfigured = false;
  private suspended = false;
  private wasMinimalBeforeSuspend = false;

  // Right-edge hot zone: OS cursor polling replaces Electron's unreliable
  // setIgnoreMouseEvents({ forward: true }) event forwarding on Windows, which
  // stops delivering mousemove while a non-Electron app is focused (a running
  // session is exactly that case). Polling getCursorScreenPoint() always works.
  private static readonly HOT_ZONE_WIDTH = 24;
  private static readonly HOTSPOT_POLL_MS = 120;
  private hotspotTimer: ReturnType<typeof setInterval> | null = null;
  private hotspotZone: 'full' | 'minimal' = 'full';
  private lastHotspot = false;

  showKioskOverlay(content: OverlayContent): void {
    this.sessionActive = false;
    this.hotspotZone = 'full';
    const sendMinimal = false; // Full mode for new sessions
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.show();
      this.kioskWindow.setIgnoreMouseEvents(false);
      this.kioskWindow.webContents.send('overlay:set-minimal', sendMinimal);
      this.kioskWindow.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
      this.startHotspotPolling();
      return;
    }

    const preloadPath = path.join(__dirname, '../../renderer/preload.js');

    this.kioskWindow = new BrowserWindow({
      fullscreen: true,
      kiosk: true,
      alwaysOnTop: true,
      frame: false,
      closable: false,
      skipTaskbar: true,
      transparent: true,
      backgroundColor: '#00000000',
      webPreferences: {
        devTools: false,
        contextIsolation: true,
        sandbox: true,
        nodeIntegration: false,
        preload: preloadPath,
      },
    });

    // Block right-click context menu
    this.kioskWindow.webContents.on('context-menu', (event) => {
      event.preventDefault();
    });

    this.kioskWindow.webContents.on('before-input-event', (event, input) => {
      const shortcut = [
        input.alt ? 'Alt' : '',
        input.control ? 'Control' : '',
        input.shift ? 'Shift' : '',
        input.meta ? 'Meta' : '',
        input.key,
      ]
        .filter(Boolean)
        .join('+');

      if (BLOCKED_SHORTCUTS.includes(shortcut)) {
        event.preventDefault();
      }
    });

    this.kioskWindow.on('closed', () => {
      this.kioskWindow = null;
      this.stopHotspotPolling();
    });

    const htmlPath = path.join(__dirname, '../../renderer/index.html');
    this.kioskWindow.loadFile(htmlPath);

    this.kioskWindow.webContents.once('did-finish-load', () => {
      this.kioskWindow?.webContents.send('overlay:set-minimal', sendMinimal);
      this.kioskWindow?.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
    });

    this.startHotspotPolling();
    this.setupPowerMonitor();
  }

  private setupPowerMonitor(): void {
    powerMonitor.on('suspend', () => this.handleSuspend());
    powerMonitor.on('resume', () => this.handleResume());
    powerMonitor.on('lock-screen', () => this.handleSuspend());
    powerMonitor.on('unlock-screen', () => this.handleResume());
  }

  private handleSuspend(): void {
    this.suspended = true;
    this.wasMinimalBeforeSuspend = this.sessionActive;
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('overlay:suspend');
    }
  }

  private async handleResume(): Promise<void> {
    this.suspended = false;
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      // Restore to full mode (not minimal)
      this.kioskWindow.show();
      this.kioskWindow.setIgnoreMouseEvents(false);
      this.kioskWindow.webContents.send('overlay:set-minimal', false);
      this.kioskWindow.webContents.send('overlay:resume');
      // Request SYNC from main process if session was active
      this.sendToOverlayAndHud('overlay:request-sync');
    }
  }

  hideKioskOverlay(): void {
    this.sessionActive = true;
    this.hotspotZone = 'minimal';
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.show();
      this.kioskWindow.webContents.send('overlay:set-minimal', true);
      this.setKioskClickThrough(true);
      this.startHotspotPolling();
    } else {
      console.warn('[Platform:Windows] hideKioskOverlay: kioskWindow is null or destroyed!');
    }
  }

  setKioskClickThrough(clickThrough: boolean): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.setIgnoreMouseEvents(clickThrough, { forward: true });
    }
  }

  /**
   * Poll the OS cursor position and notify the renderer when the Call Staff
   * hot zone is hovered/unhovered.
   *
   * The kiosk window is fullscreen, so window coordinates equal the cursor
   * position minus the window origin. This must run in the main process:
   * Electron's forwarded mouse events (setIgnoreMouseEvents + forward) are
   * unreliable on Windows — they are not delivered while a non-Electron app
   * is focused, which is exactly the state during a running session.
   */
  private startHotspotPolling(): void {
    if (this.hotspotTimer !== null) return;
    this.lastHotspot = false;
    this.hotspotTimer = setInterval(() => this.pollHotspot(), WindowsPlatformService.HOTSPOT_POLL_MS);
  }

  private stopHotspotPolling(): void {
    if (this.hotspotTimer !== null) {
      clearInterval(this.hotspotTimer);
      this.hotspotTimer = null;
    }
    this.lastHotspot = false;
  }

  private pollHotspot(): void {
    if (!this.kioskWindow || this.kioskWindow.isDestroyed()) {
      this.stopHotspotPolling();
      return;
    }
    const cursor = screen.getCursorScreenPoint();
    const bounds = this.kioskWindow.getBounds();
    const cx = cursor.x - bounds.x;
    const cy = cursor.y - bounds.y;
    const inWindow =
      cx >= 0 && cy >= 0 && cx < bounds.width && cy < bounds.height;

    let active = false;
    if (inWindow) {
      if (this.hotspotZone === 'minimal') {
        // Full-height right-edge zone (~15% of the width). It covers both the
        // edge strip and the Call Staff button (bottom right), so moving from
        // the strip onto the button never trips the auto-hide dead state.
        active = cx >= bounds.width - Math.max(WindowsPlatformService.HOT_ZONE_WIDTH, bounds.width * 0.15);
      } else {
        // Bottom-right corner zone (~15% x 15%), covering the corner trigger
        // and the Call Staff button so it stays visible while approaching it.
        active =
          cx >= bounds.width - Math.max(WindowsPlatformService.HOT_ZONE_WIDTH, bounds.width * 0.15) &&
          cy >= bounds.height - Math.max(WindowsPlatformService.HOT_ZONE_WIDTH, bounds.height * 0.15);
      }
    }

    if (active !== this.lastHotspot) {
      this.lastHotspot = active;
      this.kioskWindow.webContents.send('overlay:hotspot', active);
    }
  }

  isKioskVisible(): boolean {
    return Boolean(
      this.kioskWindow &&
        !this.kioskWindow.isDestroyed() &&
        this.kioskWindow.isVisible(),
    );
  }

  sendConfigToOverlay(config: { hasOverrideCode: boolean }): void {
    this.overrideCodeConfigured = config.hasOverrideCode;
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('agent:config', config);
    }
  }

  sendToOverlayAndHud(channel: string, data?: unknown): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send(channel, data);
    }
  }

  updateTimer(timer: { elapsedSeconds: number }): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('overlay:timer', { elapsedSeconds: timer.elapsedSeconds });
    }
  }

  sendAnnouncement(text: string, durationMs: number): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('overlay:announcement', {
        text,
        durationMs,
      });
    }
  }

  showLowTimeWarning(minutes: number): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('overlay:low-time', { minutes });
    }
  }

  async restartPC(): Promise<void> {
    if (isTestMode()) return;
    await execAsync('shutdown /r /t 0');
  }

  async shutdownPC(): Promise<void> {
    if (isTestMode()) return;
    await execAsync('shutdown /s /t 0');
  }

  async captureScreenshot(): Promise<Buffer> {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 1280, height: 720 },
    });

    if (!sources || sources.length === 0) {
      throw new Error('No screen sources available for screenshot');
    }

    const primaryScreen = sources[0];
    let pngBuffer: Buffer;

    if (primaryScreen.thumbnail) {
      pngBuffer = primaryScreen.thumbnail.toPNG();
    } else {
      throw new Error('Screenshot thumbnail not available');
    }

    try {
      const compressed = await sharp(pngBuffer)
        .resize(1280, 720, { fit: 'inside', withoutEnlargement: true })
        .jpeg({ quality: 80 })
        .toBuffer();
      return compressed;
    } catch {
      return pngBuffer;
    }
  }

  async enableAutoStart(): Promise<void> {
    if (isTestMode()) return;
    const command = `reg.exe add "${AUTO_START_KEY}" /v "${APP_NAME}" /d "${process.execPath}" /f`;
    await execAsync(command);
  }

  async disableAutoStart(): Promise<void> {
    if (isTestMode()) return;
    const command = `reg.exe delete "${AUTO_START_KEY}" /v "${APP_NAME}" /f`;
    await execAsync(command);
  }

  async getSystemInfo(): Promise<SystemInfo> {
    const [cpu, mem, disk] = await Promise.all([
      si.cpu(),
      si.mem(),
      si.diskLayout(),
    ]);

    const totalDisk = disk.reduce((acc, d) => acc + (d.size || 0), 0);

    return {
      cpuModel: cpu.brand,
      cpuCores: cpu.cores || os.cpus().length,
      totalMemoryGB: Math.floor(mem.total / 1024 / 1024 / 1024),
      totalDiskGB: Math.floor(totalDisk / 1024 / 1024 / 1024),
      osName: process.platform,
      osVersion: os.release(),
      hostname: os.hostname(),
    };
  }

  private renderKioskHtml(_content: OverlayContent): string {
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Arcade Kiosk</title>
  <style>
    body {
      margin: 0;
      padding: 0;
      background: #111;
      color: #fff;
      font-family: sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }
    #timer { font-size: 5vw; margin-top: 1rem; }
    #announcement { color: #ffd700; margin-top: 2rem; }
  </style>
</head>
<body>
  <h1 id="cafe-name"></h1>
  <div id="timer"></div>
  <div id="announcement"></div>
  <script>
    window.addEventListener('DOMContentLoaded', () => {
      document.getElementById('cafe-name').textContent = 'Arcade Kiosk';
    });
  </script>
</body>
</html>`;
  }
}
