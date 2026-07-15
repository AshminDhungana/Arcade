import { describe, it, expect, vi } from 'vitest';
import { AgentWebSocketClient } from '../../src/main/ws/client.js';
import type { AgentConfig } from '../../src/main/ws/types.js';

// ---------------------------------------------------------------------------
// Mock WebSocket (isConnected() reads WebSocket.OPEN)
// ---------------------------------------------------------------------------
class MockWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;
}
vi.stubGlobal('WebSocket', MockWebSocket);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeClient(cfg: Partial<AgentConfig>): AgentWebSocketClient {
  const full: AgentConfig = {
    server_url: 'ws://x',
    seat_id: 's1',
    agent_secret: 'sec',
    override_code_hash: null,
    master_code_hash: null,
    reconnect_max_seconds: 60,
    health_interval_seconds: 60,
    ...cfg,
  } as AgentConfig;
  // _activateOverride() calls platform.hideKioskOverlay()
  const platform = { hideKioskOverlay: vi.fn() } as any;
  return new AgentWebSocketClient(full, platform, undefined as any);
}

describe('triggerStaffOverride gate', () => {
  it('rejects master PIN when connected', async () => {
    const c = makeClient({ override_code_hash: 'AAAA', master_code_hash: 'MMMM' });
    // force "connected": state must be 'open' AND ws must be non-null + OPEN
    Object.defineProperty(c, 'state', { value: 'open', writable: true });
    (c as any).ws = { readyState: MockWebSocket.OPEN } as any;
    const r = await c.triggerStaffOverride('MMMM');
    expect(r).toBe(false);
  });

  it('accepts master PIN when disconnected', async () => {
    const c = makeClient({ master_code_hash: 'MMMM' });
    Object.defineProperty(c, 'state', { value: 'disconnected', writable: true });
    const r = await c.triggerStaffOverride('MMMM');
    expect(r).toBe('master');
  });

  it('accepts override PIN whether connected or not', async () => {
    const c = makeClient({ override_code_hash: 'AAAA' });
    Object.defineProperty(c, 'state', { value: 'disconnected', writable: true });
    const r = await c.triggerStaffOverride('AAAA');
    expect(r).toBe('override');
  });
});
