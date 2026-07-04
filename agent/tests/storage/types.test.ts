import { describe, it, expect } from 'vitest';
import type { LocalSessionCache, SessionStore } from '../../src/main/storage/types.js';

describe('storage types', () => {
  it('LocalSessionCache matches expected shape', () => {
    const cache: LocalSessionCache = {
      session_id: 'sess-123',
      seat_id: 'seat_001',
      started_at: '2026-07-04T10:00:00Z',
      local_elapsed_seconds: 0,
      disconnect_at: null,
      is_synced: false,
      status: 'ACTIVE',
      updated_at: '2026-07-04T10:00:00Z',
    };
    expect(cache.is_synced).toBe(false);
    expect(cache.status).toBe('ACTIVE');
    expect(cache.local_elapsed_seconds).toBe(0);
    expect(cache.disconnect_at).toBeNull();
  });

  it('SessionStore interface can be satisfied by a mock', () => {
    const mockStore: SessionStore = {
      init: () => {},
      persistSession: () => {},
      updateElapsed: () => {},
      markDisconnect: () => {},
      getUnsyncedSession: () => null,
      markSynced: () => {},
      clearSession: () => {},
      close: () => {},
    };
    expect(mockStore.init).toBeDefined();
    expect(mockStore.persistSession).toBeDefined();
    expect(mockStore.getUnsyncedSession).toBeDefined();
  });
});
