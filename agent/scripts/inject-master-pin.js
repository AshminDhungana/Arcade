#!/usr/bin/env node
/**
 * Build-time master PIN injection script.
 *
 * Reads a plaintext PIN from --pin, MASTER_PIN, or ARCADE_MASTER_PIN (in that
 * order), computing an Argon2id hash and generating src/main/master-pin.ts
 * with the pre-computed hash embedded. When no PIN is provided anywhere the
 * built-in default (1928) is used, so unparameterised dev builds still work.
 *
 * Usage:
 *   MASTER_PIN=1234 node scripts/inject-master-pin.js --out=src/main/master-pin.ts
 *   node scripts/inject-master-pin.js --pin=1234 --out=src/main/master-pin.ts
 *
 * The generated file exports MASTER_PIN_HASH and resolveMasterPinHash().
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { hash } from '@node-rs/argon2';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');

const MASTER_PIN_HASH_OPTIONS = {
  memoryCost: 4096,
  timeCost: 3,
  parallelism: 1,
};

/** Built-in default PIN when none is provided (matches agent/.env.example). */
const DEFAULT_MASTER_PIN = '1928';

function parseArgs() {
  const args = process.argv.slice(2);
  const result = { pin: undefined, out: '', pinProvided: false };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--pin' || arg === '-p') {
      result.pin = args[++i];
      result.pinProvided = true;
    } else if (arg === '--out' || arg === '-o') {
      result.out = args[++i];
    } else if (arg.startsWith('--pin=')) {
      result.pin = arg.slice(6);
      result.pinProvided = true;
    } else if (arg.startsWith('--out=')) {
      result.out = arg.slice(6);
    }
  }

  // Fallback to env var (MASTER_PIN, then ARCADE_MASTER_PIN)
  if (!result.pinProvided && process.env.MASTER_PIN !== undefined) {
    result.pin = process.env.MASTER_PIN;
    result.pinProvided = true;
  }
  if (!result.pinProvided && process.env.ARCADE_MASTER_PIN !== undefined) {
    result.pin = process.env.ARCADE_MASTER_PIN;
    result.pinProvided = true;
  }

  // Built-in default so unparameterised builds still get a working master PIN.
  if (!result.pinProvided) {
    result.pin = DEFAULT_MASTER_PIN;
  }

  if (!result.pin) {
    console.error('Error: PIN required. Provide via --pin, MASTER_PIN, or ARCADE_MASTER_PIN.');
    process.exit(1);
  }

  if (!result.out) {
    console.error('Error: --out path required.');
    process.exit(1);
  }

  return result;
}

async function main() {
  const { pin, out } = parseArgs();
  const outPath = path.resolve(PROJECT_ROOT, out);

  // Compute Argon2id hash
  const masterPinHash = await hash(pin, MASTER_PIN_HASH_OPTIONS);

  // Generate the master-pin.ts content
  const content = `// agent/src/main/master-pin.ts
// GENERATED AT BUILD TIME — DO NOT EDIT MANUALLY
// Run: npm run inject-master-pin (or node scripts/inject-master-pin.js)
// Plaintext PIN is provided via MASTER_PIN env var or --pin arg; only the Argon2id hash is embedded.

/** Pre-computed Argon2id hash of the emergency master PIN (injected at build time). */
export const MASTER_PIN_HASH = "${masterPinHash.replace(/"/g, '\\\\"')}";

/** Returns the pre-computed Argon2id hash of the emergency master PIN. */
export function resolveMasterPinHash() {
  return MASTER_PIN_HASH;
}
`;

  // Ensure output directory exists
  const outDir = path.dirname(outPath);
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  fs.writeFileSync(outPath, content, 'utf-8');
  console.log(`[inject-master-pin] Generated ${out} with Argon2id hash`);
}

main().catch((err) => {
  console.error('[inject-master-pin] Failed:', err);
  process.exit(1);
});
