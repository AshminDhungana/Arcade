// agent/src/main/enroll.ts
import os from 'node:os';
import { hash } from '@node-rs/argon2';
import { saveAgentConfig } from './config/loader.js';
import type { LoadedAgentConfig } from './config/types.js';
import { resolveMasterPin } from './master-pin.js';

// Argon2id parameters used to hash the emergency master PIN at enrollment.
// Kept in lockstep with tools/keygen/generate_keys.py so a pre-baked hash and a
// runtime-computed hash are interchangeable (verify() reads params from the hash).
// The algorithm defaults to Argon2id in @node-rs/argon2.
const MASTER_PIN_HASH_OPTIONS = {
  memoryCost: 4096,
  timeCost: 3,
  parallelism: 1,
} as const;

interface EnrollResponse {
  seat_id: string;
  agent_secret: string;
  cafe_name: string;
  override_code_hash: string | null;
}

export async function enrollAgent(
  serverUrl: string,
  code: string,
  configPath: string,
  intervals: { reconnect_max_seconds: number; health_interval_seconds: number },
): Promise<LoadedAgentConfig> {
  // discoverServer() returns a `ws://`/`wss://` URL for the WebSocket client;
  // fetch() rejects the `ws://` scheme, so derive an http(s) origin for the
  // enroll HTTP call (server_url stays as-is in the persisted config).
  const scheme = serverUrl.startsWith('wss://') ? 'https://' : 'http://';
  const base = scheme + serverUrl.slice(serverUrl.indexOf('://') + 3).replace(/\/$/, '');
  const res = await fetch(`${base}/api/agent/enroll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      code,
      mac_address: '',
      hostname: os.hostname(),
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`Enrollment failed (${res.status}): ${detail}`);
  }
  const data = (await res.json()) as EnrollResponse;

  // Resolve + hash the emergency master PIN (accepted only when the server is
  // unreachable). The plaintext PIN is never persisted — only the Argon2id hash
  // is written to agent.config.json. A blank PIN disables the master unlock.
  const masterPin = resolveMasterPin();
  const master_code_hash = masterPin ? await hash(masterPin, MASTER_PIN_HASH_OPTIONS) : null;

  const config: LoadedAgentConfig = {
    server_url: serverUrl,
    seat_id: data.seat_id,
    agent_secret: data.agent_secret,
    override_code_hash: data.override_code_hash ?? null,
    master_code_hash,
    cafe_name: data.cafe_name,
    reconnect_max_seconds: intervals.reconnect_max_seconds,
    health_interval_seconds: intervals.health_interval_seconds,
  };
  saveAgentConfig(config, configPath);
  return config;
}
