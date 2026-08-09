// agent/src/main/master-pin.d.ts
// Type declarations for the committed master-pin.js vitest bridge.
// The real source (master-pin.ts) is generated at build time by
// scripts/inject-master-pin.js and is gitignored; this declaration keeps
// `tsc --noEmit` working on a fresh checkout where only the .js bridge
// exists.

export const MASTER_PIN_HASH: string;

export function resolveMasterPinHash(): string;
