import { app, ipcMain } from 'electron';
import * as path from 'node:path';
import * as os from 'node:os';
import * as fs from 'node:fs';
import { getPlatformService } from './platform/index.js';
import { AgentWebSocketClient } from './ws/client.js';
import { BetterSqliteSessionStore } from './storage/session_store.js';
import { loadAgentConfig } from './config/loader.js';
import type { IPlatformService } from './platform/types.js';

let platformService: IPlatformService | null = null;
let wsClient: AgentWebSocketClient | null = null;

async function bootstrap(): Promise<void> {
  platformService = await getPlatformService();
  console.log(`[Agent] Platform service: ${platformService.constructor.name}`);

  // Load agent.config.json from the same directory as the executable.
  // In production it's next to the .exe; in dev we fall back to cwd.
  const fromExe = path.join(path.dirname(process.execPath), 'agent.config.json');
  const fromCwd = path.join(process.cwd(), 'agent.config.json');
  const configPath = fs.existsSync(fromExe) ? fromExe : fromCwd;

  let config;
  try {
    config = loadAgentConfig(configPath);
  } catch (err) {
    const message = (err as Error).message;
    console.error('[Agent] Failed to load configuration:', message);
    if (process.type === 'browser') {
      const { dialog } = await import('electron');
      dialog.showErrorBox(
        'Configuration Error',
        `Failed to load agent.config.json:\n${message}\n\n` +
        'Please ensure agent.config.json is in the same directory as the agent executable\n' +
        'and contains valid server_url, seat_id, and agent_secret values.',
      );
    }
    process.exit(1);
  }

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
}

app.whenReady().then(() => {
  bootstrap().catch((err) => {
    console.error('[Agent] Bootstrap failed:', err);
    process.exit(1);
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
