/**
 * WebSocket message types shared between frontend and backend.
 *
 * Mirrors the envelope format used in ``backend/core/ws_manager.py``
 * (SDD §9.2)::
 *
 *     {"type": "EVENT_TYPE", "payload": {...}, "timestamp": "..."}
 */

/** Event types the backend sends to dashboard clients. */
export type WSEventType =
  | 'seat_updated'
  | 'health_update'
  | 'announcement'
  | 'alert';

/** Standard WebSocket message envelope (SDD §9.2). */
export interface WSMessage<TPayload = unknown> {
  type: WSEventType;
  payload: TPayload;
  timestamp: string;
}

/** Connection lifecycle state. */
export type WSStatus = 'connecting' | 'connected' | 'disconnected';

// ---------------------------------------------------------------------------
// Payloads
// ---------------------------------------------------------------------------

/** Payload sent by the server on a `seat_updated` event. */
export interface SeatUpdatedPayload {
  /** Seat UUID — present on full seat broadcasts. */
  id?: string;
  /** Backward-compat alternative used in some code paths. */
  seat_id?: string;
  name?: string;
  zone_id?: string;
  /** One of the SeatStatus enum values. */
  status?: string;
  is_console?: boolean;
  current_session_id?: string;
  notes?: string;
  overlay_forced?: boolean;  // NEW
  /** Agent-provided on REGISTER. */
  mac_address?: string;
  /** Agent-provided on REGISTER. */
  hostname?: string;
}

/** Payload sent by the server on a `health_update` event. */
export interface HealthUpdatePayload {
  seat_id: string;
  cpu_pct: number;
  ram_pct: number;
  cpu_temp?: number;
  disk_used_gb?: number;
  disk_total_gb?: number;
  timestamp: string;
}

/** Payload sent by the server on an `announcement` event. */
export interface AnnouncementPayload {
  message: string;
  duration_seconds?: number;
}

/** Payload sent by the server on an `alert` event. */
export interface AlertPayload {
  type: string;
  seat_id: string;
  message: string;
}
