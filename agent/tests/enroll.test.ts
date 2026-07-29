import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as loader from '../src/main/config/loader.js';
import { verify } from '@node-rs/argon2';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MASTER_PIN_FILE = path.join(__dirname, '../src/main/master-pin.ts');

// Mock the master-pin module at the top level (hoisted)
// The factory will be called for each test
vi.mock('../src/main/master-pin.js', () => ({
  MASTER_PIN_HASH: '$argon2id$v=19$m=4096,t=3,p=1$fallback$salt$hash',
  resolveMasterPinHash: () => '$argon2id$v=19$m=4096,t=3,p=1$fallback$salt$hash',
}));

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

describe('enrollAgent master PIN (build-time injected)', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  afterEach(async () => {
    // Restore fallback template file
    const fallbackContent = `// agent/src/main/master-pin.ts
// FALLBACK TEMPLATE — REPLACED AT BUILD TIME by inject-master-pin.js
// Run: npm run inject-master-pin (or node scripts/inject-master-pin.js)
// Plaintext PIN is provided via MASTER_PIN env var or --pin arg; only the Argon2id hash is embedded.

/** Pre-computed Argon2id hash of the emergency master PIN (injected at build time). */
export const MASTER_PIN_HASH = "\$argon2id\$v=19\$m=4096,t=3,p=1\$fallback\$salt\$hash";

/** Returns the pre-computed Argon2id hash of the emergency master PIN. */
export function resolveMasterPinHash() {
  return MASTER_PIN_HASH;
}
`;
    await fs.writeFile(MASTER_PIN_FILE, fallbackContent, 'utf-8');
  });

  it('uses the injected master PIN hash (default test PIN)', async () => {
    const { hash } = await import('@node-rs/argon2');
    const pinHash = await hash('testpin123', { memoryCost: 4096, timeCost: 3, parallelism: 1 });

    // Re-mock with the test-specific hash
    vi.doMock('../src/main/master-pin.js', () => ({
      MASTER_PIN_HASH: pinHash,
      resolveMasterPinHash: () => pinHash,
    }));

    vi.resetModules();
    const { enrollAgent } = await import('../src/main/enroll.js');

    fakeEnrollResponse();
    const cfg = await enrollAgent('ws://localhost:8000', 'CODE', 'agent.config.json', intervals);
    expect(cfg.master_code_hash).toBeTruthy();
    expect(await verify(cfg.master_code_hash as string, 'testpin123')).toBe(true);
  });

  it('uses a different injected master PIN hash', async () => {
    const { hash } = await import('@node-rs/argon2');
    const pinHash = await hash('anotherpin456', { memoryCost: 4096, timeCost: 3, parallelism: 1 });

    vi.doMock('../src/main/master-pin.js', () => ({
      MASTER_PIN_HASH: pinHash,
      resolveMasterPinHash: () => pinHash,
    }));

    vi.resetModules();
    const { enrollAgent } = await import('../src/main/enroll.js');

    fakeEnrollResponse();
    const cfg = await enrollAgent('ws://localhost:8000', 'CODE', 'agent.config.json', intervals);
    expect(cfg.master_code_hash).toBeTruthy();
    expect(await verify(cfg.master_code_hash as string, 'anotherpin456')).toBe(true);
    expect(await verify(cfg.master_code_hash as string, 'testpin123')).toBe(false);
  });
});
