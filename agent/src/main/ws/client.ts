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
import os from 'node:os';

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

  private persistTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly config: AgentConfig,
    private readonly platform: IPlatformService,
    private readonly store?: SessionStore,
  ) {
    this.commandHandlers = createCommandHandlers(platform, {
      seatId: config.seat_id,
    }, store);
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

  /** Initiates a connection to the Arcade server. */
  connect(): void {
    if (this.state === 'connecting' || this.state === 'open') {
      return;
    }
    this.state = 'connecting';
    const url = this.buildWsUrl();
    try {
      this.ws = new WebSocket(url);
      this.ws.onopen = () => this.handleOpen();
      this.ws.onmessage = (event) => this.handleMessage(event);
      this.ws.onclose = (event) => this.handleClose(event);
      this.ws.onerror = () => this.handleError();
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

  /** Attempt staff override. Returns true if PIN verified successfully. */
  async triggerStaffOverride(pin: string): Promise<boolean> {
    if (!this.config.override_code_hash) {
      console.warn('[Agent] Staff override attempted but override_code_hash not configured');
      return false;
    }

    // NOTE: This is a timing-safe placeholder comparison.
    // Production code should use an Argon2id-aware library
    // (e.g. @node-rs/argon2) to verify against the PHC-formatted hash.
    const verified = this._timingSafeCompare(pin, this.config.override_code_hash);

    if (!verified) {
      console.warn('[Agent] Staff override PIN verification failed');
      return false;
    }

    this.overrideActive = true;
    this.platform.hideKioskOverlay();
    this.send('STAFF_OVERRIDE', {
      seat_id: this.config.seat_id,
      verified: true,
    });
    console.log('[Agent] Staff override activated');
    return true;
  }

  /** Timing-safe string comparison (prevents timing side-channel attacks). */
  private _timingSafeCompare(a: string, b: string): boolean {
    if (a.length !== b.length) return false;
    let result = 0;
    for (let i = 0; i < a.length; i++) {
      result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return result === 0;
  }

  clearOverride(): void {
    this.overrideActive = false;
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
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data as string) as WSMessage;

      // Heartbeat PONG — just clear the timeout waiting flag
      if (message.type === 'PONG') {
        this.clearHeartbeatTimeout();
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
        this.sessionState.session_id = null;
        this.sessionState.started_at = null;
      }
      if (message.type === 'RESET_OVERRIDE') {
        this.clearOverride();
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
    const wasOpen = this.state === 'open';
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
    if (wasOpen) {
      this.scheduleReconnect();
    }
  }

  private handleError(): void {
    console.error('[WS] WebSocket error');
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
      }
    }, 10_000);
  }
}
