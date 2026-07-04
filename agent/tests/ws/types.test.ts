import { describe, it, expect } from 'vitest';
import {
  type AgentConfig,
  type WSMessage,
  type ServerCommandPayloads,
  type AgentMessagePayloads,
  HEARTBEAT_INTERVAL_MS,
  HEARTBEAT_TIMEOUT_MS,
  PING_MESSAGE,
  RECONNECT_BASE_MS,
  RECONNECT_CAP_MS,
} from '../../src/main/ws/types.js';

describe('ws types', () => {
  it('all constants are defined', () => {
    expect(HEARTBEAT_INTERVAL_MS).toBe(30000);
    expect(HEARTBEAT_TIMEOUT_MS).toBe(10000);
    expect(RECONNECT_BASE_MS).toBe(1000);
    expect(RECONNECT_CAP_MS).toBe(30000);
    expect(PING_MESSAGE).toEqual({ type: 'PING', payload: {} });
  });

  it('AgentConfig has required fields', () => {
    const config: AgentConfig = {
      server_url: 'ws://192.168.1.100:8000',
      seat_id: 'seat_001',
      agent_secret: 'abc123',
    };
    expect(config.server_url).toBe('ws://192.168.1.100:8000');
    expect(config.seat_id).toBe('seat_001');
    expect(config.agent_secret).toBe('abc123');
    expect(config.override_code_hash).toBeUndefined();
  });
});
