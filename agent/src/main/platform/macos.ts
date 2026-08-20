import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promises as fs } from 'node:fs';
import os from 'os';
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
import type { IPlatformService, OverlayContent, SystemInfo } from './types.js';
import { isTestMode } from './safety.js';

const execAsync = promisify(exec);

const AUTO_START_DIR = path.join(os.homedir(), 'Library', 'LaunchAgents');
const AUTO_START_FILE = path.join(AUTO_START_DIR, 'com.neurotech.arcade.agent.plist');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BLOCKED_SHORTCUTS = [
  'Meta+q',           // Cmd+Q — quit app
  'Meta+w',           // Cmd+W — close window
  'Meta+h',           // Cmd+H — hide app
  'Meta+m',           // Cmd+M — minimize
  'Meta+Shift+i',     // Cmd+Shift+I — devtools
  'Control+Shift+i',  // Ctrl+Shift+I — devtools (fallback)
  'Control+p',        // Ctrl+P / Cmd+P — print
  'F12',              // DevTools
  'F11',              // Fullscreen toggle
  'Escape',           // Exit fullscreen
];

export class MacOSPlatformService implements IPlatformService {
  private kioskWindow: BrowserWindowType | null = null;
  private sessionActive = false;
  private overrideCodeConfigured = false;
  private suspended = false;
  private wasMinimalBeforeSuspend = false;

  // Right-edge hot zone: OS cursor polling replaces Electron's unreliable
  // setIgnoreMouseEvents({ forward: true }) event forwarding, which stops
  // delivering mousemove while another app is focused (a running session is
  // exactly that case). Polling getCursorScreenPoint() always works.
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

    const win = new BrowserWindow({
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

    win.webContents.on('context-menu', (event) => {
      event.preventDefault();
    });

    win.webContents.on('before-input-event', (event, input) => {
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

    win.on('closed', () => {
      this.kioskWindow = null;
      this.stopHotspotPolling();
    });

    const htmlPath = path.join(__dirname, '../../renderer/index.html');
    win.loadFile(htmlPath);

    this.kioskWindow = win;

    win.webContents.once('did-finish-load', () => {
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
      console.warn('[Platform:MacOS] hideKioskOverlay: kioskWindow is null or destroyed!');
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
   * unreliable — they are not delivered while another app is focused, which
   * is exactly the state during a running session.
   */
  private startHotspotPolling(): void {
    if (this.hotspotTimer !== null) return;
    this.lastHotspot = false;
    this.hotspotTimer = setInterval(() => this.pollHotspot(), MacOSPlatformService.HOTSPOT_POLL_MS);
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
        // Full-height right-edge strip (matches .kiosk-trigger-zone minimal CSS)
        active = cx >= bounds.width - MacOSPlatformService.HOT_ZONE_WIDTH;
      } else {
        // Bottom-right corner (matches the 20x20 CSS trigger zone)
        active =
          cx >= bounds.width - MacOSPlatformService.HOT_ZONE_WIDTH &&
          cy >= bounds.height - MacOSPlatformService.HOT_ZONE_WIDTH;
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
      this.kioskWindow.webContents.send('overlay:timer', {
        elapsedSeconds: timer.elapsedSeconds,
      });
    }
  }

  sendAnnouncement(text: string, durationMs: number): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('overlay:announcement', { text, durationMs });
    }
  }

  showLowTimeWarning(minutes: number): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('overlay:low-time', { minutes });
    }
  }

  async restartPC(): Promise<void> {
    if (isTestMode()) return;
    await execAsync('sudo shutdown -r now');
  }

  async shutdownPC(): Promise<void> {
    if (isTestMode()) return;
    await execAsync('sudo shutdown -h now');
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
    const plistContent = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.neurotech.arcade.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>${process.execPath}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/arcade-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/arcade-agent.err.log</string>
</dict>
</plist>`;
    await fs.mkdir(AUTO_START_DIR, { recursive: true });
    await fs.writeFile(AUTO_START_FILE, plistContent, { mode: 0o644 });
  }

  async disableAutoStart(): Promise<void> {
    if (isTestMode()) return;
    await fs.rm(AUTO_START_FILE, { force: true });
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
}
