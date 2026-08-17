import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useAvailableSeats } from './seats';
import { useAuthStore } from '@/store/authStore';

const SEATS = [
  { id: 's1', name: 'Seat 1', zone_id: 'z1', status: 'AVAILABLE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's2', name: 'Seat 2', zone_id: 'z1', status: 'ONLINE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's3', name: 'Seat 3', zone_id: 'z1', status: 'IN_USE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's4', name: 'Seat 4', zone_id: 'z1', status: 'MAINTENANCE', updated_at: '2026-01-01T00:00:00Z' },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useAvailableSeats', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok' }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('fetches and filters to AVAILABLE and ONLINE seats only', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const { result } = renderHook(() => useAvailableSeats(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.length).toBe(2);
    expect(result.current.data?.every(s => s.status === 'AVAILABLE' || s.status === 'ONLINE')).toBe(true);
  });
});
