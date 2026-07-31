// agent/src/main/master-pin.ts
// GENERATED AT BUILD TIME — DO NOT EDIT MANUALLY
// Run: npm run inject-master-pin (or node scripts/inject-master-pin.js)
// Plaintext PIN is provided via MASTER_PIN env var or --pin arg; only the Argon2id hash is embedded.

/** Pre-computed Argon2id hash of the emergency master PIN (injected at build time). */
export const MASTER_PIN_HASH = "$argon2id$v=19$m=4096,t=3,p=1$vG1lXaHy2ZmgF19kLMf86w$K5ffWrSwL1GqQeKH48MfxORB04zqSSjrdtMKCKapVXY";

/** Returns the pre-computed Argon2id hash of the emergency master PIN. */
export function resolveMasterPinHash() {
  return MASTER_PIN_HASH;
}
