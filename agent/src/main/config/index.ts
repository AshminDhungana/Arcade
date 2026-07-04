/**
 * Config module public API.
 *
 * Re-export everything needed by consumers.
 */
export { loadAgentConfig, ConfigError } from './loader.js';
export { validateAgentConfig } from './validator.js';
export type { RawAgentConfig, LoadedAgentConfig } from './types.js';
