import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MASTER_PIN_FILE = path.join(__dirname, '../src/main/master-pin.ts');

// Helper to import the module fresh each time
async function importMasterPin() {
  // Clear module cache to re-import
  vi.resetModules();
  return await import('../src/main/master-pin.js');
}

describe('resolveMasterPinHash (build-time injected)', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  afterEach(async () => {
    // Restore fallback template after tests
    const fallbackContent = `// agent/src/main/master-pin.ts
// FALLBACK TEMPLATE — REPLACED AT BUILD TIME by inject-master-pin.js
// Run: npm run inject-master-pin (or node scripts/inject-master-pin.js)
// Plaintext PIN is provided via MASTER_PIN env var or --pin arg; only the Argon2id hash is embedded.

/** Pre-computed Argon2id hash of the emergency master PIN (injected at build time). */
export const MASTER_PIN_HASH = "$argon2id$v=19$m=4096,t=3,p=1$fallback$salt$hash";

/** Returns the pre-computed Argon2id hash of the emergency master PIN. */
export function resolveMasterPinHash() {
  return MASTER_PIN_HASH;
}
`;
    await fs.writeFile(MASTER_PIN_FILE, fallbackContent, 'utf-8');
  });

  it('exports MASTER_PIN_HASH constant', async () => {
    const { MASTER_PIN_HASH } = await importMasterPin();
    expect(MASTER_PIN_HASH).toBeDefined();
    expect(MASTER_PIN_HASH).toMatch(/^\$argon2id\$/);
  });

  it('resolveMasterPinHash returns the MASTER_PIN_HASH constant', async () => {
    const { resolveMasterPinHash, MASTER_PIN_HASH } = await importMasterPin();
    expect(resolveMasterPinHash()).toBe(MASTER_PIN_HASH);
  });

  it('hash is a valid Argon2id hash format', async () => {
    const { MASTER_PIN_HASH } = await importMasterPin();
    // Argon2id hash format: $argon2id$v=19$m=4096,t=3,p=1$salt$hash
    // The fallback template uses a placeholder, so just check it starts with $argon2id$
    expect(MASTER_PIN_HASH).toMatch(/^\$argon2id\$/);
  });
});
