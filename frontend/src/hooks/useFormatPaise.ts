/**
 * Convert an integer amount in paise to a human-readable "Rs. X.XX" string.
 *
 * This is the **single source of truth** for paise→rupees conversion
 * in the entire frontend (NFR-DATA-002). All monetary display must go
 * through this function.
 *
 * @param paise - Integer amount in paise (e.g. 25050 = Rs. 250.50)
 * @returns Formatted string, e.g. "Rs. 250.50"
 */
export function formatPaise(paise: number): string {
  if (paise < 0) {
    throw new Error(`formatPaise: negative amount not allowed (got ${paise})`);
  }
  const rupees = paise / 100;
  return `Rs. ${rupees.toFixed(2)}`;
}
