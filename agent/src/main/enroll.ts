// agent/src/main/enroll.ts
import os from 'node:os';
import { saveAgentConfig } from './config/loader.js';
import type { LoadedAgentConfig } from './config/types.js';
import { MASTER_PIN_HASH } from './master-pin.js';

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
  const res = await fetch(`${serverUrl.replace(/\/$/, '')}/api/agent/enroll`, {
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
  const config: LoadedAgentConfig = {
    server_url: serverUrl,
    seat_id: data.seat_id,
    agent_secret: data.agent_secret,
    override_code_hash: data.override_code_hash ?? null,
    master_code_hash: MASTER_PIN_HASH,
    cafe_name: data.cafe_name,
    reconnect_max_seconds: intervals.reconnect_max_seconds,
    health_interval_seconds: intervals.health_interval_seconds,
  };
  saveAgentConfig(config, configPath);
  return config;
}
