import { describe, it, expect } from 'vitest';
import { validateAgentConfig } from '../../src/main/config/validator.js';

describe('validateAgentConfig', () => {
  it('returns ok for a fully valid config', () => {
    const result = validateAgentConfig({
      server_url: 'ws://192.168.1.100:8000',
      seat_id: 'seat_001',
      agent_secret: 'abc123def456',
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.config.server_url).toBe('ws://192.168.1.100:8000');
      expect(result.config.seat_id).toBe('seat_001');
      expect(result.config.agent_secret).toBe('abc123def456');
      expect(result.config.override_code_hash).toBeNull();
    }
  });

  it('returns errors when server_url is missing', () => {
    const result = validateAgentConfig({ seat_id: 'seat_001', agent_secret: 'x' });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('server_url is required and must be a string');
    }
  });

  it('returns errors when seat_id is missing', () => {
    const result = validateAgentConfig({ server_url: 'ws://x', agent_secret: 'x' });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('seat_id is required and must be a string');
    }
  });

  it('returns errors when agent_secret is missing', () => {
    const result = validateAgentConfig({ server_url: 'ws://x', seat_id: 'seat_1' });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('agent_secret is required and must be a string');
    }
  });

  it('validates server_url protocol (ws:// or wss://)', () => {
    const result = validateAgentConfig({
      server_url: 'http://192.168.1.100:8000',
      seat_id: 'seat_001',
      agent_secret: 'x',
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.includes('ws://'))).toBe(true);
    }
  });

  it('allows optional override_code_hash when present', () => {
    const result = validateAgentConfig({
      server_url: 'ws://192.168.1.100:8000',
      seat_id: 'seat_001',
      agent_secret: 'x',
      override_code_hash: '$argon2id$v=19$m=65536,t=3,p=4$hash',
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.config.override_code_hash).toBe('$argon2id$v=19$m=65536,t=3,p=4$hash');
    }
  });

  it('uses default reconnect_max_seconds (60)', () => {
    const result = validateAgentConfig({
      server_url: 'ws://192.168.1.100:8000',
      seat_id: 'seat_001',
      agent_secret: 'x',
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.config.reconnect_max_seconds).toBe(60);
    }
  });

  it('uses default health_interval_seconds (60)', () => {
    const result = validateAgentConfig({
      server_url: 'ws://192.168.1.100:8000',
      seat_id: 'seat_001',
      agent_secret: 'x',
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.config.health_interval_seconds).toBe(60);
    }
  });

  it('rejects non-object config', () => {
    const result = validateAgentConfig('not an object');
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('Config must be a JSON object');
    }
  });

  it('rejects negative reconnect_max_seconds', () => {
    const result = validateAgentConfig({
      server_url: 'ws://192.168.1.100:8000',
      seat_id: 'seat_001',
      agent_secret: 'x',
      reconnect_max_seconds: -1,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors).toContain('reconnect_max_seconds must be a positive number');
    }
  });
});
