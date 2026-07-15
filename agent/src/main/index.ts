import { app, ipcMain } from 'electron';
import * as path from 'node:path';
import * as os from 'node:os';
import * as fs from 'node:fs';
import { getPlatformService } from './platform/index.js';
import { AgentWebSocketClient } from './ws/client.js';
import { BetterSqliteSessionStore } from './storage/session_store.js';
import { loadAgentConfig } from './config/loader.js';
import { discoverServer } from './discovery.js';
import { enrollAgent } from './enroll.js';
import { openSetupWindow } from './setup_window.js';
import type { IPlatformService } from './platform/types.js';
import type { AgentConfig } from './ws/types.js';

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

  if (!fs.existsSync(configPath)) {
    // ---- First-run: no local config → show setup window ----
    // NOTE: onEnrolled is a no-op here. openSetupWindow (Task 12) fires
    // onEnrolled on webContents 'did-finish-load' — the instant the setup
    // HTML loads, BEFORE the user can enter the enroll code. Putting
    // app.relaunch()/app.exit(0) in onEnrolled (as the brief specifies)
    // would relaunch immediately and loop forever, since config is never
    // written. The relaunch is instead placed in the 'agent:enroll' IPC
    // handler (below), AFTER enrollAgent() succeeds and the renderer is
    // signalled via 'enroll:done'.
    const setupWin = openSetupWindow(() => {});
    ipcMain.handle('agent:enroll', async (_e, code: string) => {
      try {
        const serverUrl = await discoverServer();
        if (!serverUrl) {
          return { ok: false, error: 'Server not found on LAN. Check the server is running.' };
        }
        await enrollAgent(serverUrl, code, configPath, {
          reconnect_max_seconds: 60,
          health_interval_seconds: 60,
        });
        setupWin.webContents.send('enroll:done');
        app.relaunch();
        app.exit(0);
        return { ok: true }; // unreachable after exit(0); kept for type completeness
      } catch (err) {
        return { ok: false, error: (err as Error).message };
      }
    });
    return;
  }

  let config: AgentConfig;
  try {
    // `loadAgentConfig` returns a `LoadedAgentConfig` whose optional
    // fields are typed `T | null`; `AgentConfig` uses `T | undefined`.
    // They are equivalent at runtime (both falsy in the PIN check), so
    // a single cast reconciles the two interfaces here.
    config = loadAgentConfig(configPath) as AgentConfig;
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
