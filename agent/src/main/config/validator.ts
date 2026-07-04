/**
 * Configuration validation for the Arcade Agent.
 *
 * Validates raw `agent.config.json` values and applies defaults.
 */

import type { LoadedAgentConfig } from './types.js';

export type ValidationResult =
  | { ok: true; config: LoadedAgentConfig }
  | { ok: false; errors: string[] };

/**
 * Validate a raw configuration object loaded from `agent.config.json`.
 *
 * @param raw The parsed JSON value from the config file.
 * @returns A `ValidationResult` — either `{ok: true, config: LoadedAgentConfig}`
 *          or `{ok: false, errors: string[]}`.
 */
export function validateAgentConfig(raw: unknown): ValidationResult {
  const errors: string[] = [];

  if (raw === null || typeof raw !== 'object') {
    return { ok: false, errors: ['Config must be a JSON object'] };
  }

  const r = raw as Record<string, unknown>;

  // server_url — must start with ws:// or wss://
  if (!r.server_url || typeof r.server_url !== 'string') {
    errors.push('server_url is required and must be a string');
  } else if (!r.server_url.match(/^wss?:\/\//)) {
    errors.push('server_url must start with ws:// or wss://');
  }

  // seat_id
  if (!r.seat_id || typeof r.seat_id !== 'string') {
    errors.push('seat_id is required and must be a string');
  }

  // agent_secret
  if (!r.agent_secret || typeof r.agent_secret !== 'string') {
    errors.push('agent_secret is required and must be a string');
  }

  // override_code_hash — optional, must be string or null
  let override_code_hash: string | null = null;
  if (r.override_code_hash !== undefined && r.override_code_hash !== null) {
    if (typeof r.override_code_hash !== 'string') {
      errors.push('override_code_hash must be a string or null');
    } else {
      override_code_hash = r.override_code_hash;
    }
  }

  // reconnect_max_seconds — optional, default 60
  let reconnect_max_seconds = 60;
  if (r.reconnect_max_seconds !== undefined) {
    if (typeof r.reconnect_max_seconds !== 'number' || r.reconnect_max_seconds <= 0) {
      errors.push('reconnect_max_seconds must be a positive number');
    } else {
      reconnect_max_seconds = r.reconnect_max_seconds;
    }
  }

  // health_interval_seconds — optional, default 60
  let health_interval_seconds = 60;
  if (r.health_interval_seconds !== undefined) {
    if (typeof r.health_interval_seconds !== 'number' || r.health_interval_seconds <= 0) {
      errors.push('health_interval_seconds must be a positive number');
    } else {
      health_interval_seconds = r.health_interval_seconds;
    }
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    config: {
      server_url: r.server_url as string,
      seat_id: r.seat_id as string,
      agent_secret: r.agent_secret as string,
      override_code_hash,
      reconnect_max_seconds,
      health_interval_seconds,
    },
  };
}
