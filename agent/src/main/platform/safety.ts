/**
 * Guard helper for destructive platform commands.
 *
 * Vitest sets NODE_ENV=test (and VITEST=true). While a test runner is
 * active, commands that reboot/shutdown the machine or modify the system
 * (registry, autostart entries) must never execute — even if a test's
 * command mocks leak and a real exec/fs call would otherwise fire.
 */

export function isTestMode(): boolean {
  return process.env.NODE_ENV === 'test' || process.env.VITEST === 'true';
}
