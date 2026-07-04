import { app, BrowserWindow } from 'electron';
import { getPlatformService } from './platform/index.js';

function createWindow(): void {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    title: 'Arcade Agent',
  });
  win.loadURL('data:text/html,<h1>Arcade Agent (scaffold)</h1>');
}

async function bootstrap(): Promise<void> {
  const platform = await getPlatformService();
  console.log(`Platform service initialised: ${platform.constructor.name}`);
  // TODO: WebSocket client, session store, tray (Features 2.2.2-2.2.5)
}

app.whenReady().then(() => {
  createWindow();
  bootstrap().catch((err) => {
    console.error('Bootstrap failed:', err);
    process.exit(1);
  });
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
