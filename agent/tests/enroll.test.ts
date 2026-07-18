import { describe, it, expect, vi, beforeEach } from 'vitest';
import { enrollAgent } from '../src/main/enroll.js';
import * as loader from '../src/main/config/loader.js';
import { verify } from '@node-rs/argon2';

// Stub Argon2 so we exercise real verify() round-trip against the value enroll
// writes. Uses the default @node-rs/argon2 options (Argon2id, m=4096 t=3 p=1).
vi.mock('@node-rs/argon2', async () => {
  const actual = await vi.importActual<typeof import('@node-rs/argon2')>('@node-rs/argon2');
  return { ...actual };
});

// Capture the config enrollAgent would persist instead of touching disk.
vi.mock('../src/main/config/loader.js', async () => {
  const actual = await vi.importActual<typeof loader>('../src/main/config/loader.js');
  return { ...actual, saveAgentConfig: vi.fn() };
});

const intervals = { reconnect_max_seconds: 60, health_interval_seconds: 60 };

function fakeEnrollResponse(override: unknown = null) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      ok: true,
      json: async () => ({
        seat_id: 'seat-1',
        agent_secret: 'secret',
        cafe_name: 'Test Cafe',
        override_code_hash: override,
      }),
      text: async () => '',
    })),
  );
}

describe('enrollAgent master PIN', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    delete process.env.ARCADE_MASTER_PIN;
    vi.clearAllMocks();
  });

  it('hashes the default master PIN (1928) when env is unset', async () => {
    fakeEnrollResponse();
    const cfg = await enrollAgent('ws://localhost:8000', 'CODE', 'agent.config.json', intervals);
    expect(cfg.master_code_hash).toBeTruthy();
    expect(await verify(cfg.master_code_hash as string, '1928')).toBe(true);
  });

  it('hashes ARCADE_MASTER_PIN when provided', async () => {
    vi.stubEnv('ARCADE_MASTER_PIN', '2468');
    fakeEnrollResponse();
    const cfg = await enrollAgent('ws://localhost:8000', 'CODE', 'agent.config.json', intervals);
    expect(await verify(cfg.master_code_hash as string, '2468')).toBe(true);
    expect(await verify(cfg.master_code_hash as string, '1928')).toBe(false);
  });

  it('disables the master PIN (null hash) when ARCADE_MASTER_PIN is blank', async () => {
    vi.stubEnv('ARCADE_MASTER_PIN', '');
    fakeEnrollResponse();
    const cfg = await enrollAgent('ws://localhost:8000', 'CODE', 'agent.config.json', intervals);
    expect(cfg.master_code_hash).toBeNull();
  });
});
