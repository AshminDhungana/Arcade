import type { Staff } from '@/store/authStore';

const API_BASE = '/api';

/** JSON response shape from POST /api/auth/login. */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  staff: Staff;
}

/**
 * Thrown when the login endpoint returns a non-2xx status.
 *
 * On a 429 (rate limited), `retryAfter` contains the number of seconds
 * the user must wait before trying again.
 */
export class AuthError extends Error {
  readonly status: number;
  readonly retryAfter: number | null;

  constructor(message: string, status: number, retryAfter: number | null = null) {
    super(message);
    this.name = 'AuthError';
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

/**
 * Authenticate a staff member with their staff ID and PIN.
 *
 * @param staffId - e.g. "STAFF-001"
 * @param pin     - 4-20 character PIN
 * @returns TokenResponse on success
 * @throws AuthError on any non-2xx response
 */
export async function login(staffId: string, pin: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ staff_id: staffId, pin }),
  });

  if (!res.ok) {
    const retryAfter =
      res.status === 429
        ? parseInt(res.headers.get('Retry-After') ?? '0', 10) || null
        : null;
    const body = await res.json().catch(() => ({ detail: 'Authentication failed' }));
    throw new AuthError(body.detail ?? 'Authentication failed', res.status, retryAfter);
  }

  return (await res.json()) as TokenResponse;
}
