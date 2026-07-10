// frontend/src/api/sessions.test.ts
import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fetchSession } from './sessions';

const mockToken = 'test-jwt-token';

beforeEach(() => {
  vi.resetAllMocks();
  globalThis.fetch = vi.fn();
});

describe('fetchSession', () => {
  it('calls GET /api/sessions/{id} with auth header', async () => {
    const mockSession = { id: 'sess_1', seat_id: 'seat_1', locked_rate_paise: 500 };
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockSession),
    } as Response);

    const result = await fetchSession('sess_1', mockToken);

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/sessions/sess_1', {
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mockToken}` },
    });
    expect(result).toEqual(mockSession);
  });

  it('throws on non-ok response', async () => {
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    } as Response);

    await expect(fetchSession('sess_1', mockToken)).rejects.toThrow('Failed to fetch session: 404 Not Found');
  });
});
