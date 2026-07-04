import { BrowserWindow, desktopCapturer } from 'electron';
import { exec } from 'child_process';
import { promisify } from 'util';
import sharp from 'sharp';
import si from 'systeminformation';
import os from 'os';
import type { IPlatformService, OverlayContent, SystemInfo } from './types.js';

const execAsync = promisify(exec);

const AUTO_START_KEY = 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run';
const APP_NAME = 'ArcadeAgent';

const BLOCKED_SHORTCUTS = [
  'Alt+F4',
  'Alt+Shift+I',
  'Control+Shift+I',
  'Control+P',
  'F12',
];

export class WindowsPlatformService implements IPlatformService {
  private kioskWindow: BrowserWindow | null = null;

  showKioskOverlay(content: OverlayContent): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.show();
      this.kioskWindow.webContents.send('overlay:update', content);
      return;
    }

    this.kioskWindow = new BrowserWindow({
      fullscreen: true,
      kiosk: true,
      alwaysOnTop: true,
      frame: false,
      closable: false,
      skipTaskbar: true,
      webPreferences: {
        devTools: false,
        contextIsolation: true,
        sandbox: true,
        nodeIntegration: false,
      },
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
    });

    const initialHtml = this.renderKioskHtml(content);
    this.kioskWindow.loadURL(
      `data:text/html,${encodeURIComponent(initialHtml)}`,
    );
  }

  hideKioskOverlay(): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.hide();
      this.kioskWindow.destroy();
    }
    this.kioskWindow = null;
  }

  updateTimer(timeString: string): void {
    if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
      this.kioskWindow.webContents.send('overlay:timer', { timeString });
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

  async restartPC(): Promise<void> {
    await execAsync('shutdown /r /t 0');
  }

  async shutdownPC(): Promise<void> {
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
    } catch (_err) {
      return pngBuffer;
    }
  }

  async enableAutoStart(): Promise<void> {
    const command = `reg.exe add "${AUTO_START_KEY}" /v "${APP_NAME}" /d "${process.execPath}" /f`;
    await execAsync(command);
  }

  async disableAutoStart(): Promise<void> {
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
