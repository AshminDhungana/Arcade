/**
 * Better-sqlite3-based session store for the Arcade agent.
 *
 * Provides synchronous SQLite persistence so session state survives
 * crashes and reconnections. Used by the WebSocket client to cache
 * session data before sending a SYNC message after reconnection.
 */

import Database from 'better-sqlite3';
import type { LocalSessionCache, SessionStore, LocalSessionStatus } from './types.js';

export class BetterSqliteSessionStore implements SessionStore {
  private db: Database.Database | null = null;

  constructor(private readonly dbPath: string = ':memory:') {}

  /** Initialise the database and create the schema. */
  init(): void {
    this.db = new Database(this.dbPath);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        seat_id TEXT NOT NULL,
        started_at TEXT NOT NULL,
        local_elapsed_seconds INTEGER NOT NULL DEFAULT 0,
        disconnect_at TEXT,
        is_synced INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        updated_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_sessions_is_synced ON sessions(is_synced);
    `);
  }

  /** Persist a new session when HIDE_OVERLAY is received. */
  persistSession(sessionId: string, seatId: string, startedAt: string): void {
    if (!this.db) throw new Error('DB not initialised. Call init() first.');
    const sql = this.db.prepare(`
      INSERT INTO sessions (session_id, seat_id, started_at, local_elapsed_seconds, disconnect_at, is_synced, status, updated_at)
      VALUES (?, ?, ?, 0, ?, 0, 'ACTIVE', ?)
      ON CONFLICT(session_id) DO UPDATE SET
        seat_id = excluded.seat_id,
        started_at = excluded.started_at,
        local_elapsed_seconds = excluded.local_elapsed_seconds,
        disconnect_at = excluded.disconnect_at,
        is_synced = excluded.is_synced,
        status = excluded.status,
        updated_at = excluded.updated_at;
    `);
    sql.run(sessionId, seatId, startedAt, null, new Date().toISOString());
  }

  /** Update elapsed time (called every 10s during active session). */
  updateElapsed(sessionId: string, elapsedSeconds: number): void {
    if (!this.db) throw new Error('DB not initialised. Call init() first.');
    const sql = this.db.prepare(`
      UPDATE sessions
      SET local_elapsed_seconds = ?, updated_at = ?
      WHERE session_id = ?;
    `);
    sql.run(elapsedSeconds, new Date().toISOString(), sessionId);
  }

  /** Record disconnect timestamp on WS close. */
  markDisconnect(sessionId: string, disconnectAt: string): void {
    if (!this.db) throw new Error('DB not initialised. Call init() first.');
    const sql = this.db.prepare(`
      UPDATE sessions
      SET disconnect_at = ?, updated_at = ?
      WHERE session_id = ?;
    `);
    sql.run(disconnectAt, new Date().toISOString(), sessionId);
  }

  /** Retrieve the first unsynced session for the SYNC payload. */
  getUnsyncedSession(): LocalSessionCache | null {
    if (!this.db) throw new Error('DB not initialised. Call init() first.');
    const sql = this.db.prepare(`
      SELECT * FROM sessions WHERE is_synced = 0 LIMIT 1;
    `);
    const row = sql.get() as Record<string, unknown> | undefined;
    if (!row) return null;
    return this.mapRow(row);
  }

  /** Mark a session as synced after a successful SYNC ack from the server. */
  markSynced(sessionId: string): void {
    if (!this.db) throw new Error('DB not initialised. Call init() first.');
    const sql = this.db.prepare(`
      UPDATE sessions
      SET is_synced = 1, updated_at = ?
      WHERE session_id = ?;
    `);
    sql.run(new Date().toISOString(), sessionId);
  }

  /** Clear local cache when session ends (SHOW_OVERLAY). */
  clearSession(sessionId: string): void {
    if (!this.db) throw new Error('DB not initialised. Call init() first.');
    const sql = this.db.prepare(`DELETE FROM sessions WHERE session_id = ?;`);
    sql.run(sessionId);
  }

  /** Close the database connection. */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }

  private mapRow(row: Record<string, unknown>): LocalSessionCache {
    return {
      session_id: String(row.session_id),
      seat_id: String(row.seat_id),
      started_at: String(row.started_at),
      local_elapsed_seconds: Number(row.local_elapsed_seconds || 0),
      disconnect_at: row.disconnect_at ? String(row.disconnect_at) : null,
      is_synced: row.is_synced === 1 || row.is_synced === true,
      status: String(row.status) as LocalSessionStatus,
      updated_at: String(row.updated_at),
    };
  }
}
