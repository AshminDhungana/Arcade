/**
 * WebSocket types and constants for the Arcade Agent client.
 *
 * All messages use the standard JSON envelope (SDD Section 9.2):
 *   { "type": "EVENT_TYPE", "payload": {...}, "timestamp": "..." }
 */

// ---------------------------------------------------------------------------
// Timing constants (SDD Section 9.5, TODO.md Section 2.2.2)
// ---------------------------------------------------------------------------

/** Interval between PING messages (milliseconds). */
export const HEARTBEAT_INTERVAL_MS = 30_000;

/** Time to wait for PONG before declaring connection dead (milliseconds). */
export const HEARTBEAT_TIMEOUT_MS = 10_000;

/** Base reconnect delay (milliseconds). */
export const RECONNECT_BASE_MS = 1_000;

/** Maximum reconnect delay (milliseconds). */
export const RECONNECT_CAP_MS = 30_000;

// ---------------------------------------------------------------------------
// Pre-built messages
// ---------------------------------------------------------------------------

/** PING message sent by the agent to the server. */
export const PING_MESSAGE: WSMessage = { type: 'PING', payload: {} };

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

/** Agent configuration loaded from `agent.config.json`. */
export interface AgentConfig {
  /** WebSocket server URL, e.g. `ws://192.168.1.100:8000`. */
  server_url: string;

  /** Seat identifier, e.g. `seat_001`. */
  seat_id: string;

  /** Secret token shared with the server for authentication. */
  agent_secret: string;

  /** Optional Argon2id hash of the staff override PIN. */
  override_code_hash?: string | null;

  /** Optional Argon2id hash of the emergency master PIN. */
  master_code_hash?: string | null;

  /** Optional: maximum reconnect delay in seconds (default 60). */
  reconnect_max_seconds?: number;

  /** Optional: health metrics interval in seconds (default 60). */
  health_interval_seconds?: number;

  /** Optional: whether the kiosk overlay is currently forced ON by staff override. */
  overlayForced?: boolean;
}

// ---------------------------------------------------------------------------
// Message envelope
// ---------------------------------------------------------------------------

/** Standard WebSocket message envelope. */
export interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp?: string;
}

// ---------------------------------------------------------------------------
// Server -> Agent commands
// ---------------------------------------------------------------------------

/** All command types the server can send to the agent. */
export type ServerCommandType =
  | 'HIDE_OVERLAY'
  | 'SHOW_OVERLAY'
  | 'SHOW_MESSAGE'
  | 'RESTART'
  | 'SHUTDOWN'
  | 'TAKE_SCREENSHOT'
  | 'LOW_TIME_WARNING'
  | 'RESET_OVERRIDE'
  | 'FORCE_OVERLAY_ON'
  | 'FORCE_OVERLAY_OFF';

/** Payload shapes for each server command. */
export interface ServerCommandPayloads {
  HIDE_OVERLAY: { session_id: string; started_at: string; duration_minutes?: number };
  SHOW_OVERLAY: { session_id: string };
  SHOW_MESSAGE: { text: string; duration_seconds: number };
  RESTART: { delay_seconds?: number };
  SHUTDOWN: { delay_seconds?: number };
  TAKE_SCREENSHOT: Record<string, never>;
  LOW_TIME_WARNING: { minutes_remaining: number };
  RESET_OVERRIDE: Record<string, never>;
  FORCE_OVERLAY_ON: { session_id?: string; reason?: string };
  FORCE_OVERLAY_OFF: { session_id?: string; reason?: string };
}

// ---------------------------------------------------------------------------
// Agent -> Server messages
// ---------------------------------------------------------------------------

/** All message types the agent can send to the server. */
export type AgentMessageType = 'REGISTER' | 'SYNC' | 'HEALTH' | 'STAFF_OVERRIDE' | 'STAFF_ALERT' | 'PING' | 'SCREENSHOT_RESULT';

/** Payload shapes for each agent message. */
export interface AgentMessagePayloads {
  REGISTER: {
    seat_id: string;
    mac_address: string;
    hostname: string;
    cpu_model: string;
    ram_gb: number;
    os_version: string;
    os: string;
    agent_version: string;
  };
  SYNC: {
    session_id: string;
    local_elapsed_seconds: number;
    disconnect_at: string;
    reconnect_at: string;
  };
  HEALTH: {
    cpu_percent: number;
    ram_percent: number;
    cpu_temp_celsius: number | null;
    disk_used_gb: number;
    disk_total_gb: number;
  };
  STAFF_OVERRIDE: {
    seat_id: string;
    verified: boolean;
  };
  PING: Record<string, never>;
  STAFF_ALERT: {
    seat_id: string;
    timestamp: string;
  };
  SCREENSHOT_RESULT: {
    seat_id: string;
    image_base64: string;
    captured_at: string;
  };
}
// Re-export storage types for WebSocket client usage
export type { LocalSessionCache, SessionStore } from '../storage/types.js';
