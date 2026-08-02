// agent/src/main/enroll.ts
import os from 'node:os';
import { saveAgentConfig } from './config/loader.js';
import type { LoadedAgentConfig } from './config/types.js';
import { resolveMasterPinHash } from './master-pin.js';

const ENROLL_TIMEOUT_MS = 10000;

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

  console.log('[enrollAgent] Enrolling with server:', base, 'code:', code);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), ENROLL_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${base}/api/agent/enroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        mac_address: '',
        hostname: os.hostname(),
      }),
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof DOMException && err.name === 'AbortError') {
      console.error('[enrollAgent] Enrollment request timed out');
      throw new Error('Enrollment request timed out (10s)');
    }
    console.error('[enrollAgent] Enrollment fetch error:', err);
    throw err;
  }
  clearTimeout(timeout);

  console.log('[enrollAgent] Response status:', res.status);
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    console.error('[enrollAgent] Enrollment failed:', res.status, detail);
    throw new Error(`Enrollment failed (${res.status}): ${detail}`);
  }
  const data = (await res.json()) as EnrollResponse;
  console.log('[enrollAgent] Enrollment successful:', data.seat_id);

  // Use pre-computed master PIN hash (injected at build time).
  // The plaintext PIN is never present at runtime — only the Argon2id hash is embedded.
  const master_code_hash = resolveMasterPinHash();

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
