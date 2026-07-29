// agent/src/main/master-pin.js
// Re-export from TypeScript source for vitest compatibility
// This file is used as a bridge for vitest to resolve the module

export const MASTER_PIN_HASH = "$argon2id$v=19$m=4096,t=3,p=1$fallback$salt$hash";
export function resolveMasterPinHash() {
  return MASTER_PIN_HASH;
}
