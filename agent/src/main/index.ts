import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'node:path';
import * as os from 'node:os';
import * as fs from 'node:fs';
import { getPlatformService } from './platform/index.js';
import { AgentWebSocketClient } from './ws/client.js';
import { BetterSqliteSessionStore } from './storage/session_store.js';
import type { IPlatformService } from './platform/types.js';

function createWindow(): void {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    title: 'Arcade Agent',
  });
  win.loadURL('data:text/html,<h1>Arcade Agent (scaffold)</h1>');
}

let platformService: IPlatformService | null = null;
let wsClient: AgentWebSocketClient | null = null;

async function bootstrap(): Promise<void> {
  platformService = await getPlatformService();
  console.log(`[Agent] Platform service: ${platformService.constructor.name}`);

  // TODO: Replace with actual config loading from agent.config.json (Feature 2.2.5)
  const config = {
    server_url: 'ws://localhost:8000',
    seat_id: 'seat_001',
    agent_secret: 'replace-me-in-feature-2.2.5',
  };

  // Create data directory and initialise the session store
  const dbDir = path.join(os.homedir(), '.arcade-agent');
  if (!fs.existsSync(dbDir)) {
    fs.mkdirSync(dbDir, { recursive: true });
  }
  const dbPath = path.join(dbDir, 'sessions.db');
  const sessionStore = new BetterSqliteSessionStore(dbPath);
  sessionStore.init();

  wsClient = new AgentWebSocketClient(config, platformService, sessionStore);
  wsClient.connect();
  console.log('[Agent] WebSocket client connecting...');

  // -----------------------------------------------------------------
  // IPC handlers: renderer → main
  // -----------------------------------------------------------------

  ipcMain.on('call-staff', () => {
    // Forward to server; no-op if offline (logged by ws client)
    wsClient?.send('STAFF_ALERT', {
      seat_id: config.seat_id,
      timestamp: new Date().toISOString(),
    });
  });

  ipcMain.on('staff-override', (_event, pin: string) => {
    void wsClient?.triggerStaffOverride(pin);
  });

  // TODO: Feature 2.2.5 -- Config loading from agent.config.json
}

app.whenReady().then(() => {
  createWindow();
  bootstrap().catch((err) => {
    console.error('[Agent] Bootstrap failed:', err);
    process.exit(1);
  });
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

process.on('SIGTERM', () => {
  console.log('[Agent] SIGTERM received, disconnecting...');
  wsClient?.disconnect();
  process.exit(0);
});
