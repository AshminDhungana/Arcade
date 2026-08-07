import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promises as fs } from 'node:fs';
import os from 'os';
import { BrowserWindow, desktopCapturer } from 'electron';
import { exec } from 'child_process';
import { promisify } from 'util';
import sharp from 'sharp';
import si from 'systeminformation';
import type { IPlatformService, OverlayContent, SystemInfo } from './types.js';

const execAsync = promisify(exec);

const AUTO_START_DIR = path.join(os.homedir(), '.config', 'autostart');
const AUTO_START_FILE = path.join(AUTO_START_DIR, 'arcade-agent.desktop');

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

/** True when running under a native Wayland session. */
export function isWayland(): boolean {
  return (
    process.env.XDG_SESSION_TYPE === 'wayland' ||
    Boolean(process.env.WAYLAND_DISPLAY)
  );
}

export class LinuxPlatformService implements IPlatformService {
  private kioskWindow: BrowserWindow | null = null;
  private sessionActive = false;
  private overrideCodeConfigured = false;

  showKioskOverlay(content: OverlayContent): void {
    this.sessionActive = false;
    const sendMinimal = false; // Full mode for new sessions
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.show();
      this.kioskWindow.webContents.send('overlay:set-minimal', sendMinimal);
      this.kioskWindow.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
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

    if (isWayland()) {
      win.setKiosk(true);
      win.maximize();
      win.setAlwaysOnTop(true, 'screen-saver');
      console.warn(
        '[linux] Wayland detected: kiosk overlay is NOT bypass-proof. ' +
          'Deploy under a Wayland kiosk compositor (Cage / gnome-kiosk / ubuntu-frame) ' +
          'for true lockdown. See docs/agent-setup.md.',
      );
    }

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
    });

    const htmlPath = path.join(__dirname, '../../renderer/index.html');
    win.loadFile(htmlPath);

    this.kioskWindow = win;

    win.webContents.once('did-finish-load', () => {
      this.kioskWindow?.webContents.send('overlay:set-minimal', sendMinimal);
      this.kioskWindow?.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
    });
  }

  hideKioskOverlay(): void {
    console.log('[Platform:Linux] hideKioskOverlay: START');
    this.sessionActive = true;
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      console.log('[Platform:Linux] hideKioskOverlay: window exists, sending overlay:set-minimal=true');
      this.kioskWindow.show();
      this.kioskWindow.webContents.send('overlay:set-minimal', true);
      console.log('[Platform:Linux] hideKioskOverlay: message sent');
    } else {
      console.warn('[Platform:Linux] hideKioskOverlay: kioskWindow is null or destroyed!');
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
    try {
      await execAsync('systemctl reboot');
    } catch {
      await execAsync('loginctl reboot');
    }
  }

  async shutdownPC(): Promise<void> {
    try {
      await execAsync('systemctl poweroff');
    } catch {
      await execAsync('loginctl poweroff');
    }
  }

  async captureScreenshot(): Promise<Buffer> {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 1280, height: 720 },
    });

    if (!sources || sources.length === 0) {
      throw new Error(
        'Screenshot unavailable on this session (no screen sources; Wayland/PipeWire ' +
          'portal not permitted or X11 display absent).',
      );
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
    const desktopEntry = [
      '[Desktop Entry]',
      'Type=Application',
      'Name=Arcade Agent',
      `Exec=${process.execPath}`,
      'X-GNOME-Autostart-enabled=true',
      'X-GNOME-Autostart-Delay=5',
      '',
    ].join('\n');
    await fs.mkdir(AUTO_START_DIR, { recursive: true });
    await fs.writeFile(AUTO_START_FILE, desktopEntry, { mode: 0o644 });
  }

  async disableAutoStart(): Promise<void> {
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
