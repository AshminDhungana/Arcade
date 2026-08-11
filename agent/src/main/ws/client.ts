/**
 * Agent WebSocket Client
 *
 * Manages the full WebSocket lifecycle for the Arcade agent.
 */

import type { IPlatformService } from '../platform/types.js';
import type { SessionStore } from '../storage/types.js';
import {
  type AgentConfig,
  type WSMessage,
  type AgentMessagePayloads,
  HEARTBEAT_INTERVAL_MS,
  HEARTBEAT_TIMEOUT_MS,
  RECONNECT_BASE_MS,
  RECONNECT_CAP_MS,
} from './types.js';
import { createCommandHandlers } from './commands.js';
import { saveAgentConfig } from '../config/loader.js';
import type { LoadedAgentConfig } from '../config/types.js';
import os from 'node:os';
import { verify } from '@node-rs/argon2';


type ConnectionState = 'connecting' | 'open' | 'closing' | 'disconnected';

export class AgentWebSocketClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private reconnectAttempts = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeoutTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private healthTimer: ReturnType<typeof setInterval> | null = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private commandHandlers: Record<string, (payload: any) => void | Promise<void>>;
  private sessionState: {
    session_id: string | null;
    started_at: string | null;
    local_elapsed: number;
  } = { session_id: null, started_at: null, local_elapsed: 0 };
  /** Whether a staff override is currently active. */
  public overrideActive = false;

  /** Cafe name fetched from the server on REGISTERED. */
  public cafeName = '';

  /** Event banner fetched from the server on REGISTERED (empty = hidden). */
  public eventBanner = '';

  /** Queue for STAFF_OVERRIDE events when server is offline. */
  private overrideEventQueued = false;

  private persistTimer: ReturnType<typeof setInterval> | null = null;
  private onRendererEvent?: (event: string, data?: unknown) => void;

  constructor(
    private readonly config: AgentConfig,
    private readonly platform: IPlatformService,
    private readonly store?: SessionStore,
    private readonly configPath: string = '',
    onRendererEvent?: (event: string, data?: unknown) => void,
  ) {
    this.onRendererEvent = onRendererEvent;
    this.commandHandlers = createCommandHandlers(platform, {
      seatId: config.seat_id,
      serverUrl: config.server_url,
      agentSecret: config.agent_secret,
      getCafeName: () => this.cafeName,
      getEventBanner: () => this.eventBanner,
    }, store);

    // Seed the brand from the persisted config (written at enrollment) so the
    // overlay is branded immediately at boot, before the first REGISTERED.
    this.cafeName = (config.cafe_name ?? '').trim();
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /** Is the WebSocket currently open and connected? */
  isConnected(): boolean {
    return (
      this.state === 'open' &&
      this.ws !== null &&
      this.ws.readyState === WebSocket.OPEN
    );
  }

  /** Returns the current connection state. */
  getConnectionState(): ConnectionState {
    return this.state;
  }

  /** Is the a staff override currently active? */
  isOverrideActiveBool(): boolean {
    return this.overrideActive;
  }

  /** Cafe name reported by the server (empty until REGISTERED arrives). */
  getCafeName(): string {
    return this.cafeName;
  }

  /** Initiates a connection to the Arcade server. */
  connect(): void {
    if (this.state === 'connecting' || this.state === 'open') {
      return;
    }
    this.state = 'connecting';
    const url = this.buildWsUrl();
    try {
      this.ws = new WebSocket(url);
      const connectionTimeout = setTimeout(() => {
        if (this.state === 'connecting' && this.ws) {
          console.warn('[WS] Connection timeout (10s) — closing socket');
          this.ws.close();
        }
      }, 10_000);

      this.ws.onopen = () => {
        clearTimeout(connectionTimeout);
        this.handleOpen();
      };
      this.ws.onmessage = (event) => this.handleMessage(event);
      this.ws.onclose = (event) => this.handleClose(event);
      this.ws.onerror = (event) => this.handleError(event);
    } catch {
      this.scheduleReconnect();
    }
  }

  /** Closes the connection and cancels any pending reconnect. */
  disconnect(): void {
    this.clearAllTimers();
    this.state = 'disconnected';
    if (this.ws) {
      try { this.ws.close(); } catch { /* best effort */ }
      this.ws = null;
    }
  }

  /** Send a typed message to the server (returns true if sent). */
  send<T extends keyof AgentMessagePayloads>(
    type: T,
    payload: AgentMessagePayloads[T],
  ): boolean {
    if (!this.isConnected() || !this.ws) {
      return false;
    }
    const message: WSMessage = {
      type,
      payload: payload as Record<string, unknown>,
      timestamp: new Date().toISOString(),
    };
    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch {
      return false;
    }
  }

  // -------------------------------------------------------------------------
  // Session helpers
  // -------------------------------------------------------------------------

  recordSessionStart(session_id: string, started_at: string): void {
    this.sessionState = {
      session_id,
      started_at,
      local_elapsed: 0,
    };
    this.store?.persistSession(session_id, this.config.seat_id, started_at);
    this.startElapsedTimer();
  }

  recordSessionEnd(): void {
    if (this.sessionState.session_id) {
      this.store?.clearSession(this.sessionState.session_id);
    }
    if (this.persistTimer) {
      clearInterval(this.persistTimer);
      this.persistTimer = null;
    }
    this.sessionState = {
      session_id: null,
      started_at: null,
      local_elapsed: 0,
    };
  }

  /**
   * Verify a PIN and unlock. The staff override PIN always works when it is
   * configured; the build-injected master PIN is the emergency fallback and
   * works in every connection state. Returns 'override' | 'master' | false.
   */
  async triggerStaffOverride(pin: string): Promise<'override' | 'master' | false> {
    const overrideHash = this.config.override_code_hash;
    const masterHash = this.config.master_code_hash ?? null;

    // Always allow the staff override PIN if configured and it verifies.
    if (overrideHash && (await this.safeVerifyPin(overrideHash, pin))) {
      this._activateOverride();
      return 'override';
    }
    // Master PIN is the emergency unlock — accepted in any state (it is
    // build-injected per installation and never shown in the UI).
    if (masterHash && (await this.safeVerifyPin(masterHash, pin))) {
      this._activateOverride();
      return 'master';
    }
    console.warn('[Agent] PIN verification failed');
    return false;
  }

  /** Verify against an Argon2id hash, treating malformed hashes as a mismatch. */
  private async safeVerifyPin(hash: string, pin: string): Promise<boolean> {
    try {
      return await verify(hash, pin);
    } catch (err) {
      console.error('[Agent] PIN verification error (hash may be malformed):', err);
      return false;
    }
  }

  /**
   * Verify a PIN against the stored override_code_hash.
   * Unlike triggerStaffOverride, this does NOT activate override or hide overlay.
   * Returns true if PIN matches.
   */
  async triggerSettingsPinVerify(pin: string): Promise<boolean> {
    const overrideHash = this.config.override_code_hash;
    if (!overrideHash) return false;
    try {
      return await verify(overrideHash, pin);
    } catch {
      return false;
    }
  }

  private _activateOverride(): void {
    this.overrideActive = true;
    this.platform.hideKioskOverlay();
    if (this.isConnected()) {
      this.send('STAFF_OVERRIDE', { seat_id: this.config.seat_id, verified: true });
      this.overrideEventQueued = false;
    } else {
      this.overrideEventQueued = true;
      console.log('[WS] STAFF_OVERRIDE event queued (server offline)');
    }
    console.log('[Agent] Override activated');
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private _applyServerPush(type: string, payload: any): void {
    if (type === 'SET_OVERRIDE_PIN') {
      this.config.override_code_hash = payload.override_code_hash ?? null;
      if (this.configPath) saveAgentConfig(this.config as LoadedAgentConfig, this.configPath);
      // Re-sync the renderer so Ctrl+Shift+O reflects the new PIN state.
      this.platform.sendConfigToOverlay({ hasOverrideCode: Boolean(this.config.override_code_hash) });
    }
  }

  clearOverride(): void {
    this.overrideActive = false;
    this.overrideEventQueued = false;
  }

  // -------------------------------------------------------------------------
  // Private: Event handlers
  // -------------------------------------------------------------------------

  private handleOpen(): void {
    const wasReconnect = this.reconnectAttempts > 0;
    this.state = 'open';
    this.reconnectAttempts = 0;
    this.startHeartbeat();
    this.startHealthMetrics();
    void this.sendRegister();
    if (wasReconnect && this.sessionState.session_id) {
      this.sendSyncOnReconnect();
    }
    // Flush queued STAFF_OVERRIDE event if override is active
    if (this.overrideActive && this.overrideEventQueued) {
      this.send('STAFF_OVERRIDE', {
        seat_id: this.config.seat_id,
        verified: true,
      });
      this.overrideEventQueued = false;
      console.log('[WS] Flushed queued STAFF_OVERRIDE event on reconnect');
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data as string) as WSMessage;
      this._applyServerPush(message.type, message.payload);

      // Heartbeat PONG — just clear the timeout waiting flag
      if (message.type === 'PONG') {
        this.clearHeartbeatTimeout();
        return;
      }

      // Server heartbeat: reply PONG so the server keeps the seat online.
      if (message.type === 'PING') {
        this.send('PONG', {});
        return;
      }

      // Screenshot is handled directly by the client
      if (message.type === 'TAKE_SCREENSHOT') {
        void this.handleScreenshot();
        return;
      }

      // Update session tracking for overlay commands
      if (message.type === 'HIDE_OVERLAY') {
        const payload = message.payload as { session_id: string; started_at: string };
        this.sessionState.session_id = payload.session_id;
        this.sessionState.started_at = payload.started_at;
      }
      if (message.type === 'SHOW_OVERLAY') {
        // Suppress SHOW_OVERLAY when staff override is active
        if (this.overrideActive) {
          console.log('[WS] SHOW_OVERLAY_SUPPRESSED_BY_OVERRIDE');
          return;
        }
        this.sessionState.session_id = null;
        this.sessionState.started_at = null;
      }
      if (message.type === 'RESET_OVERRIDE') {
        this.clearOverride();
      }

      // Handle SYNC_ACK from server after successful reconciliation
      if (message.type === 'SYNC_ACK') {
        const payload = message.payload as { session_id: string | undefined };
        if (payload.session_id) {
          this.store?.markSynced(payload.session_id);
          console.log(`[WS] SYNC_ACK received for session: ${payload.session_id}`, payload);
        }
        return;
      }

      // Capture the cafe name so SHOW_OVERLAY can brand the kiosk (Epic 5.5).
      if (message.type === 'REGISTERED') {
        const payload = (message.payload ?? {}) as {
          cafe_name?: string;
          event_banner?: string;
        };
        const cafeName = typeof payload.cafe_name === 'string' ? payload.cafe_name.trim() : '';
        if (cafeName) {
          this.cafeName = cafeName;
          if (this.configPath) {
            // Persist so the brand survives restarts even if REGISTERED is missed.
            this.config.cafe_name = cafeName;
            saveAgentConfig(this.config as LoadedAgentConfig, this.configPath);
          }
        }
        if (payload.event_banner) {
          this.eventBanner = payload.event_banner;
        }
        return;
      }

      // Handle STAFF_ALERT_ACK from server - forward to renderer for toast notification
      if (message.type === 'STAFF_ALERT_ACK') {
        this.onRendererEvent?.('staff-alert-ack');
        return;
      }

      // Delegate to command handler
      const handler = this.commandHandlers[message.type];
      if (handler) {
        try {
          void handler(message.payload);
        } catch (err) {
          console.error(`[WS] Handler error for ${message.type}:`, err);
        }
      } else {
        console.warn(`[WS] Unknown command type: ${message.type}`);
      }
    } catch (err) {
      console.error('[WS] Message parse error:', err);
    }
  }

  private handleClose(_event: CloseEvent): void {
    if (this.sessionState.session_id) {
      // Track disconnect time for SYNC on reconnect
      this.sessionState.local_elapsed =
        Date.now() - (this.sessionState.started_at ? new Date(this.sessionState.started_at).getTime() : Date.now());
      // Record disconnect in local SQLite for crash recovery
      this.store?.markDisconnect(this.sessionState.session_id, new Date().toISOString());
    }
    this.state = 'disconnected';
    this.clearAllTimers();
    this.ws = null;
    // Always schedule reconnect on close, not just after a successful connection
    this.scheduleReconnect();
  }

  private handleError(event: Event): void {
    console.error('[WS] WebSocket error:', (event as ErrorEvent)?.message || event);
    this.state = 'disconnected';
    this.clearAllTimers();
    this.ws = null;
    this.scheduleReconnect();
  }

  // -------------------------------------------------------------------------
  // Private: Message builders
  // -------------------------------------------------------------------------

  private async sendRegister(): Promise<void> {
    if (!this.isConnected()) return;

    let macAddress = 'unknown';
    try {
      const ifaces = Object.values(os.networkInterfaces());
      for (const iface of ifaces) {
        if (!iface) continue;
        for (const entry of iface) {
          if (!entry.internal && entry.mac) {
            macAddress = entry.mac;
            break;
          }
        }
        if (macAddress !== 'unknown') break;
      }
    } catch {
      macAddress = 'unknown';
    }

    const info = await this.platform.getSystemInfo();
    this.send('REGISTER', {
      seat_id: this.config.seat_id,
      mac_address: macAddress,
      hostname: info.hostname,
      cpu_model: info.cpuModel,
      ram_gb: info.totalMemoryGB,
      os_version: info.osVersion,
      os: info.osName,
      agent_version: '0.0.0',
    });
  }

  private sendSyncOnReconnect(): void {
    if (!this.sessionState.session_id || !this.sessionState.started_at) return;

    const now = new Date().toISOString();
    const startedAtMs = new Date(this.sessionState.started_at).getTime();
    const elapsedSeconds = Math.floor((Date.now() - startedAtMs) / 1000);

    this.send('SYNC', {
      session_id: this.sessionState.session_id,
      local_elapsed_seconds: elapsedSeconds,
      disconnect_at: now,
      reconnect_at: now,
    });
  }

  private async sendHealthMetrics(): Promise<void> {
    if (!this.isConnected()) return;

    try {
      const si = await import('systeminformation');
      const [cpu, mem, temp, disk] = await Promise.all([
        si.default.currentLoad(),
        si.default.mem(),
        si.default.cpuTemperature(),
        si.default.fsSize(),
      ]);
      const d = disk[0];
      this.send('HEALTH', {
        cpu_percent: Math.round(cpu.currentLoad ?? 0),
        ram_percent: Math.round(((mem.used ?? 0) / (mem.total ?? 1)) * 100),
        cpu_temp_celsius: temp.main ?? null,
        disk_used_gb: d ? Math.round((d.size - d.available) / 1e9) : 0,
        disk_total_gb: d ? Math.round(d.size / 1e9) : 0,
      });
    } catch (err) {
      console.error('[WS] Health metrics error:', err);
    }
  }

  private async handleScreenshot(): Promise<void> {
    try {
      const buffer = await this.platform.captureScreenshot();
      this.send('SCREENSHOT_RESULT', {
        seat_id: this.config.seat_id,
        image_base64: buffer.toString('base64'),
        captured_at: new Date().toISOString(),
      });
    } catch (err) {
      console.error('[WS] Screenshot error:', err);
    }
  }

  // -------------------------------------------------------------------------
  // Private: Heartbeat
  // -------------------------------------------------------------------------

  private startHeartbeat(): void {
    this.clearAllTimers();
    this.heartbeatTimer = setInterval(() => this.sendPing(), HEARTBEAT_INTERVAL_MS);
  }

  private sendPing(): void {
    if (!this.isConnected()) return;
    this.send('PING', {});
    this.heartbeatTimeoutTimer = setTimeout(() => {
      console.warn('[WS] Heartbeat timeout — reconnecting');
      this.ws?.close();
    }, HEARTBEAT_TIMEOUT_MS);
  }

  private clearHeartbeatTimeout(): void {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  // -------------------------------------------------------------------------
  // Private: Health metrics
  // -------------------------------------------------------------------------

  private startHealthMetrics(): void {
    const intervalMs = (this.config.health_interval_seconds ?? 60) * 1000;
    this.healthTimer = setInterval(() => this.sendHealthMetrics(), intervalMs);
  }

  // -------------------------------------------------------------------------
  // Private: Reconnection
  // -------------------------------------------------------------------------

  private scheduleReconnect(): void {
    if (this.state === 'connecting' || this.state === 'open') {
      return;
    }
    const delay = this.calculateReconnectDelay();
    console.log(`[WS] Reconnecting in ${delay}ms`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts += 1;
      this.connect();
    }, delay);
  }

  private calculateReconnectDelay(): number {
    const base = RECONNECT_BASE_MS * Math.pow(2, this.reconnectAttempts);
    const capped = Math.min(base, RECONNECT_CAP_MS);
    const jitter = capped * 0.1 * (Math.random() * 2 - 1);
    return Math.max(0, Math.floor(capped + jitter));
  }

  // -------------------------------------------------------------------------
  // Private: Utilities
  // -------------------------------------------------------------------------

  private buildWsUrl(): string {
    const { server_url, seat_id, agent_secret } = this.config;
    return `${server_url.replace(/\/$/, '')}/ws/agent/${seat_id}?secret=${encodeURIComponent(agent_secret)}`;
  }

  private clearAllTimers(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.clearHeartbeatTimeout();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.healthTimer) {
      clearInterval(this.healthTimer);
      this.healthTimer = null;
    }
    if (this.persistTimer) {
      clearInterval(this.persistTimer);
      this.persistTimer = null;
    }
  }

  private startElapsedTimer(): void {
    if (this.persistTimer) {
      clearInterval(this.persistTimer);
      this.persistTimer = null;
    }
    this.persistTimer = setInterval(() => {
      if (this.sessionState.session_id && this.sessionState.started_at) {
        const elapsed = Math.floor(
          (Date.now() - new Date(this.sessionState.started_at).getTime()) / 1000,
        );
        this.store?.updateElapsed(this.sessionState.session_id, elapsed);
        this.platform.updateTimer({ elapsedSeconds: elapsed });
      }
    }, 10_000);
  }
}
