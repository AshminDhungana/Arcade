// agent/src/main/master-pin.ts
//
// Emergency master PIN for the Arcade Agent.
//
// This is the ONLY credential that can unlock the kiosk overlay while the
// agent cannot reach the server (see src/main/ws/client.ts `triggerStaffOverride`).
// When the server is reachable, only the staff override PIN works.
//
// The plaintext PIN is NEVER persisted. During enrollment (src/main/enroll.ts)
// the resolved PIN is hashed with Argon2id — the same algorithm/params used for
// staff override PINs — and stored as `master_code_hash` in agent.config.json.
//
// Resolution order:
//   1. ARCADE_MASTER_PIN environment variable (or a value loaded from .env)
//   2. The built-in DEFAULT_MASTER_PIN below
// A blank ARCADE_MASTER_PIN disables the emergency master PIN entirely.
//
// See agent/.env.example. To override per deployment, set ARCADE_MASTER_PIN in
// the environment, or copy .env.example → .env and edit it.

import * as fs from 'node:fs';
import * as path from 'node:path';

/** Built-in default emergency master PIN (used when ARCADE_MASTER_PIN is unset). */
export const DEFAULT_MASTER_PIN = '1928';

const ENV_VAR = 'ARCADE_MASTER_PIN';

// Minimal zero-dependency .env loader so ARCADE_MASTER_PIN can be supplied via a
// local .env file (copy agent/.env.example → agent/.env). It only fills missing
// variables and never overrides a real environment variable.
function loadDotEnv(): void {
  const file = path.join(process.cwd(), '.env');
  let raw: string;
  try {
    raw = fs.readFileSync(file, 'utf-8');
  } catch {
    return; // no .env present — nothing to load
  }
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('//')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (value.length >= 2 && value.startsWith('"') && value.endsWith('"')) {
      value = value.slice(1, -1);
    }
    if (key && process.env[key] === undefined) process.env[key] = value;
  }
}

/**
 * Resolve the emergency master PIN to hash at enrollment.
 * Returns '' when explicitly disabled (blank ARCADE_MASTER_PIN).
 */
export function resolveMasterPin(): string {
  if (process.env[ENV_VAR] === undefined) loadDotEnv();
  const value = process.env[ENV_VAR];
  return value !== undefined ? value : DEFAULT_MASTER_PIN;
}
