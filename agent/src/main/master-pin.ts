// agent/src/main/master-pin.ts
// BUILD-INJECTED — do NOT commit a real value.
// The seller sets MASTER_PIN_HASH for each cafe at packaging time
// (hash the master PIN with the same Argon2id params as override PINs).
// When absent, the emergency master PIN is disabled.
export const MASTER_PIN_HASH: string | null = null;
