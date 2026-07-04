/**
 * Configuration types for the Arcade Agent.
 *
 * Defines the raw JSON shape as it appears on disk and the
 * fully-validated, defaulted shape used at runtime.
 */

/** Shape of `agent.config.json` as it appears on disk. */
export interface RawAgentConfig {
  server_url: string;
  seat_id: string;
  agent_secret: string;
  override_code_hash?: string | null;
  reconnect_max_seconds?: number;
  health_interval_seconds?: number;
}

/** Fully validated config with defaults applied. */
export interface LoadedAgentConfig {
  server_url: string;
  seat_id: string;
  agent_secret: string;
  override_code_hash: string | null;
  reconnect_max_seconds: number;
  health_interval_seconds: number;
}
