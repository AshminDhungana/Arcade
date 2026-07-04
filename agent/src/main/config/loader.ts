/**
 * Configuration file loader for the Arcade Agent.
 *
 * Reads `agent.config.json` from disk, parses JSON, and validates
 * the contents before returning a `LoadedAgentConfig`.
 */

import * as fs from 'node:fs';
import { validateAgentConfig } from './validator.js';
import type { LoadedAgentConfig } from './types.js';

/**
 * Thrown when the configuration file is missing, unreadable,
 * contains invalid JSON, or fails validation.
 */
export class ConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigError';
  }
}

/**
 * Load and validate the agent configuration from a file path.
 *
 * @param configPath Absolute or relative path to `agent.config.json`.
 * @returns A `LoadedAgentConfig` with all defaults applied.
 * @throws ConfigError if the file is missing, unparseable, or invalid.
 */
export function loadAgentConfig(configPath: string): LoadedAgentConfig {
  let raw: string;
  try {
    raw = fs.readFileSync(configPath, 'utf-8');
  } catch (err) {
    const code = (err as { code?: string }).code;
    if (code === 'ENOENT') {
      throw new ConfigError(
        `agent.config.json not found at ${configPath}. Run the setup wizard.`,
      );
    }
    throw new ConfigError(
      `Failed to read agent.config.json: ${(err as Error).message}`,
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new ConfigError('agent.config.json contains invalid JSON.');
  }

  const result = validateAgentConfig(parsed);
  if (!result.ok) {
    throw new ConfigError(
      `agent.config.json validation failed:\n  - ${result.errors.join('\n  - ')}`,
    );
  }

  return result.config;
}
