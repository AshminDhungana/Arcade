import { describe, it, expect, vi, beforeEach } from 'vitest';
import { resolveMasterPin, DEFAULT_MASTER_PIN } from '../src/main/master-pin.js';

describe('resolveMasterPin', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    // Ensure a stray ARCADE_MASTER_PIN from the host env can't skew the default case.
    delete process.env.ARCADE_MASTER_PIN;
  });

  it('returns the built-in default when no env var is set', () => {
    expect(resolveMasterPin()).toBe(DEFAULT_MASTER_PIN);
    expect(DEFAULT_MASTER_PIN).toBe('1928');
  });

  it('prefers ARCADE_MASTER_PIN over the default', () => {
    vi.stubEnv('ARCADE_MASTER_PIN', '5555');
    expect(resolveMasterPin()).toBe('5555');
  });

  it('returns an empty string when ARCADE_MASTER_PIN is blank (disables master PIN)', () => {
    vi.stubEnv('ARCADE_MASTER_PIN', '');
    expect(resolveMasterPin()).toBe('');
  });
});
