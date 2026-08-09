// agent/src/main/setup_window.ts
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import electron from 'electron';
import type { BrowserWindow as BrowserWindowType } from 'electron';
const { BrowserWindow } = electron;

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function openSetupWindow(
  onEnrolled: () => void,
): BrowserWindowType {
  const win = new BrowserWindow({
    width: 520,
    height: 360,
    frame: true,
    resizable: false,
    webPreferences: {
      devTools: true,
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      preload: path.join(__dirname, '../renderer/preload.js'),
    },
  });
  win.webContents.once('did-finish-load', onEnrolled);
  win.loadFile(path.join(__dirname, '../renderer/setup.html'));
  return win;
}
