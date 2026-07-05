/** Seat status values from backend SeatStatus enum. */
export const SeatStatus = {
  AVAILABLE: 'AVAILABLE',
  IN_USE: 'IN_USE',
  RESERVED: 'RESERVED',
  PAUSED: 'PAUSED',
  MAINTENANCE: 'MAINTENANCE',
  OFFLINE: 'OFFLINE',
  BOOTING: 'BOOTING',
  UNREACHABLE: 'UNREACHABLE',
} as const;

export type SeatStatus = (typeof SeatStatus)[keyof typeof SeatStatus];

/** Full Seat entity as returned by `GET /api/seats`. */
export interface Seat {
  id: string;
  name: string;
  zone_id: string;
  mac_address: string | null;
  status: SeatStatus;
  plug_id: string | null;
  is_console: boolean;
  notes: string | null;
  wol_attempts: number;
  wol_successes: number;
  wol_failures: number;
  created_at: string;
  updated_at: string;
}
