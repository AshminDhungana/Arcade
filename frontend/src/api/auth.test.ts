import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { login, AuthError } from './auth';

describe('login()', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns token response on success', async () => {
    const mockResponse = {
      access_token: 'tok-123',
      token_type: 'bearer',
      expires_in: 28800,
      staff: { id: 'STAFF-001', name: 'Alice', role: 'ADMIN', is_active: true },
    };
    window.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 201,
        json: () => Promise.resolve(mockResponse),
      } as Response),
    );

    const result = await login('STAFF-001', '1111');
    expect(result.access_token).toBe('tok-123');
    expect(result.staff.name).toBe('Alice');

    // Verify the correct endpoint and body were used
    expect(window.fetch).toHaveBeenCalledWith('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ staff_id: 'STAFF-001', pin: '1111' }),
    });
  });

  it('throws AuthError on 401 (wrong PIN)', async () => {
    window.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({ detail: 'Invalid staff ID or PIN' }),
      } as Response),
    );

    await expect(login('STAFF-001', '0000')).rejects.toThrow(AuthError);
  });

  it('throws AuthError with retryAfter on 429 (lockout)', async () => {
    window.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers({ 'Retry-After': '900' }),
        json: () => Promise.resolve({ detail: 'Too many failed login attempts' }),
      } as Response),
    );

    try {
      await login('STAFF-001', '0000');
      expect.fail('Expected AuthError to be thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(AuthError);
      expect((err as AuthError).retryAfter).toBe(900);
    }
  });

  it('throws AuthError with null retryAfter when no Retry-After header on 429', async () => {
    window.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        headers: new Headers(),
        json: () => Promise.resolve({ detail: 'Too many failed login attempts' }),
      } as Response),
    );

    try {
      await login('STAFF-001', '0000');
      expect.fail('Expected AuthError to be thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(AuthError);
      expect((err as AuthError).retryAfter).toBeNull();
    }
  });
});

describe('AuthError', () => {
  it('carries status and retryAfter', () => {
    const err = new AuthError('Too many attempts', 429, 900);
    expect(err.status).toBe(429);
    expect(err.retryAfter).toBe(900);
    expect(err.message).toBe('Too many attempts');
    expect(err.name).toBe('AuthError');
  });
});
