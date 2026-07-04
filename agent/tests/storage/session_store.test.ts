import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { BetterSqliteSessionStore } from '../../src/main/storage/session_store.js';

describe('BetterSqliteSessionStore', () => {
  let store: BetterSqliteSessionStore;

  beforeEach(() => {
    store = new BetterSqliteSessionStore(':memory:');
    store.init();
  });

  afterEach(() => {
    store.close();
  });

  it('persists a session and retrieves it', () => {
    store.persistSession('sess-1', 'seat_001', '2026-07-04T10:00:00Z');
    const session = store.getUnsyncedSession();
    expect(session?.session_id).toBe('sess-1');
    expect(session?.seat_id).toBe('seat_001');
    expect(session?.is_synced).toBe(false);
    expect(session?.status).toBe('ACTIVE');
    expect(session?.local_elapsed_seconds).toBe(0);
    expect(session?.disconnect_at).toBeNull();
  });

  it('updates elapsed time', () => {
    store.persistSession('sess-1', 'seat_001', '2026-07-04T10:00:00Z');
    store.updateElapsed('sess-1', 120);
    const session = store.getUnsyncedSession();
    expect(session?.local_elapsed_seconds).toBe(120);
  });

  it('records a disconnect', () => {
    store.persistSession('sess-1', 'seat_001', '2026-07-04T10:00:00Z');
    store.markDisconnect('sess-1', '2026-07-04T10:02:30Z');
    const session = store.getUnsyncedSession();
    expect(session?.disconnect_at).toBe('2026-07-04T10:02:30Z');
  });

  it('marks a session as synced', () => {
    store.persistSession('sess-1', 'seat_001', '2026-07-04T10:00:00Z');
    store.markSynced('sess-1');
    expect(store.getUnsyncedSession()).toBeNull();
  });

  it('clears a session', () => {
    store.persistSession('sess-1', 'seat_001', '2026-07-04T10:00:00Z');
    store.clearSession('sess-1');
    expect(store.getUnsyncedSession()).toBeNull();
  });

  it('updates existing session on re-persist', () => {
    store.persistSession('sess-1', 'seat_001', '2026-07-04T10:00:00Z');
    store.updateElapsed('sess-1', 120);
    // Re-persist should reset elapsed but keep other fields
    store.persistSession('sess-1', 'seat_002', '2026-07-04T11:00:00Z');
    const session = store.getUnsyncedSession();
    expect(session?.seat_id).toBe('seat_002');
    expect(session?.local_elapsed_seconds).toBe(0);
    expect(session?.is_synced).toBe(false);
  });
});
