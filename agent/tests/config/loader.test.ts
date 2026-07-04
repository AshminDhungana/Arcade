import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { loadAgentConfig, ConfigError } from '../../src/main/config/loader.js';

describe('loadAgentConfig', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-config-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('loads a valid config file', () => {
    const configPath = path.join(tmpDir, 'agent.config.json');
    fs.writeFileSync(
      configPath,
      JSON.stringify({
        server_url: 'ws://192.168.1.100:8000',
        seat_id: 'seat_001',
        agent_secret: 'secret-123',
      }),
    );

    const config = loadAgentConfig(configPath);
    expect(config.server_url).toBe('ws://192.168.1.100:8000');
    expect(config.seat_id).toBe('seat_001');
    expect(config.agent_secret).toBe('secret-123');
    expect(config.override_code_hash).toBeNull();
    expect(config.health_interval_seconds).toBe(60);
    expect(config.reconnect_max_seconds).toBe(60);
  });

  it('throws ConfigError when file does not exist', () => {
    const configPath = path.join(tmpDir, 'missing.config.json');
    expect(() => loadAgentConfig(configPath)).toThrow(ConfigError);
    expect(() => loadAgentConfig(configPath)).toThrow('not found');
  });

  it('throws ConfigError for invalid JSON', () => {
    const configPath = path.join(tmpDir, 'agent.config.json');
    fs.writeFileSync(configPath, 'not valid json {');
    expect(() => loadAgentConfig(configPath)).toThrow(ConfigError);
    expect(() => loadAgentConfig(configPath)).toThrow('JSON');
  });

  it('throws ConfigError with details when validation fails', () => {
    const configPath = path.join(tmpDir, 'agent.config.json');
    fs.writeFileSync(
      configPath,
      JSON.stringify({ server_url: 'http://x', seat_id: 123 }),
    );
    expect(() => loadAgentConfig(configPath)).toThrow(ConfigError);
  });

  it('loads a config with all optional fields', () => {
    const configPath = path.join(tmpDir, 'agent.config.json');
    fs.writeFileSync(
      configPath,
      JSON.stringify({
        server_url: 'wss://10.0.0.1:443',
        seat_id: 'seat_042',
        agent_secret: 'super-secret-hex',
        override_code_hash: '$argon2id$v=19$m=65536,t=3,p=4$hash',
        reconnect_max_seconds: 120,
        health_interval_seconds: 30,
      }),
    );

    const config = loadAgentConfig(configPath);
    expect(config.server_url).toBe('wss://10.0.0.1:443');
    expect(config.seat_id).toBe('seat_042');
    expect(config.agent_secret).toBe('super-secret-hex');
    expect(config.override_code_hash).toBe('$argon2id$v=19$m=65536,t=3,p=4$hash');
    expect(config.reconnect_max_seconds).toBe(120);
    expect(config.health_interval_seconds).toBe(30);
  });
});
