/** Status of a locally cached session */
export type LocalSessionStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED';

/** Local cache of a session's state, persisted to SQLite */
export interface LocalSessionCache {
  /** Unique session identifier */
  session_id: string;
  /** Seat identifier, e.g. seat_001 */
  seat_id: string;
  /** ISO-8601 timestamp when the session started */
  started_at: string;
  /** Elapsed time in seconds, updated every 10s */
  local_elapsed_seconds: number;
  /** ISO-8601 timestamp of disconnect, or null if still connected */
  disconnect_at: string | null;
  /** Whether the server has acknowledged a SYNC for this session */
  is_synced: boolean;
  /** Current session status */
  status: LocalSessionStatus;
  /** ISO-8601 timestamp of the last local update */
  updated_at: string;
}

/** Interface for the session store (allows test doubles) */
export interface SessionStore {
  /** Initialise the database (create schema if needed) */
  init(): void;

  /** Persist session start */
  persistSession(sessionId: string, seatId: string, startedAt: string): void;

  /** Update the elapsed time counter */
  updateElapsed(sessionId: string, elapsedSeconds: number): void;

  /** Record a disconnect timestamp */
  markDisconnect(sessionId: string, disconnectAt: string): void;

  /** Retrieve an unsynced session for the SYNC payload */
  getUnsyncedSession(): LocalSessionCache | null;

  /** Mark a session as synced after a successful SYNC ack */
  markSynced(sessionId: string): void;

  /** Clear the local cache after session end */
  clearSession(sessionId: string): void;

  /** Close the database connection */
  close(): void;
}
