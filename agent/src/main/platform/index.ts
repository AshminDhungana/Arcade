import type { IPlatformService } from './types.js';
export * from './types.js';

/**
 * Map of platform names to their implementation module paths.
 *
 * Only `win32` is implemented in Feature 2.2.1.
 * `darwin` (macOS) and `linux` are planned for Phase 7.
 */
const PLATFORM_MODULES: Record<string, string> = {
  win32: './windows.js',
  darwin: './macos.js',
  linux: './linux.js',
};

/**
 * Return the platform-specific IPlatformService implementation.
 *
 * Uses `process.platform` to determine the target module dynamically.
 * Only `win32` is currently supported; `darwin` and `linux` will throw.
 *
 * @throws {Error} if the current platform is not yet supported.
 */
export async function getPlatformService(): Promise<IPlatformService> {
  const platform = process.platform;

  if (!PLATFORM_MODULES[platform]) {
    throw new Error(
      `Platform "${platform}" is not yet supported. Supported: ${Object.keys(PLATFORM_MODULES).join(', ')}.`,
    );
  }

  if (platform === 'win32') {
    const { WindowsPlatformService } = await import('./windows.js');
    return new WindowsPlatformService();
  }

  // Fallback guard — should be unreachable due to PLATFORM_MODULES check above.
  throw new Error(`Platform "${platform}" is not yet supported.`);
}
