/** Seat status values from backend SeatStatus enum. */
export const SeatStatus = {
  AVAILABLE: 'AVAILABLE',
  ONLINE: 'ONLINE',
  IN_USE: 'IN_USE',
  RESERVED: 'RESERVED',
  PAUSED: 'PAUSED',
  MAINTENANCE: 'MAINTENANCE',
  OFFLINE: 'OFFLINE',
  BOOTING: 'BOOTING',
  UNREACHABLE: 'UNREACHABLE',
  EXPIRED: 'EXPIRED',
} as const;

export type SeatStatus = (typeof SeatStatus)[keyof typeof SeatStatus];

/** Full Seat entity as returned by `GET /api/seats`. */
export interface Seat {
  id: string;
  name: string;
  zone_id: string;
  zone_name?: string;
  mac_address: string | null;
  status: SeatStatus;
  plug_id: string | null;
  is_console: boolean;
  notes: string | null;
  overlay_forced: boolean;
  assigned_end_at: string | null;  // Epic 6.5.4: active session's assigned expiry; null when no limit set
  /** Maintenance downtime tracking (C.11): UTC ISO when the seat was marked
   *  MAINTENANCE; null when not under maintenance. */
  maintenance_since: string | null;
  /** Live downtime in seconds, computed server-side while MAINTENANCE. */
  maintenance_duration_seconds: number | null;
  wol_attempts: number;
  wol_successes: number;
  wol_failures: number;
  /** Active session ID, populated via WebSocket `seat_updated` events. */
  current_session_id?: string;
  /** Active session start time (ISO), used by the elapsed timer. Populated by
   *  GET /api/seats from the active session on the seat. */
  current_session_started_at?: string;
  created_at: string;
  updated_at: string;
}
