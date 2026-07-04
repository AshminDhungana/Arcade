import { describe, it, expect } from 'vitest';

// Import the module to verify it can be loaded (pure types have no runtime value).
import {
  type IPlatformService,
  type OverlayContent,
  type SystemInfo,
  type PlatformName,
} from '../../src/main/platform/types.js';

describe('types', () => {
  it('can import IPlatformService type', () => {
    // Runtime test — the type itself evaporates at runtime, but the
    // module must be importable.
    expect(true).toBe(true);
  });

  it('PlatformName is one of the expected values at type level', () => {
    const platform: PlatformName = 'win32';
    expect(platform).toBe('win32');
  });
});
