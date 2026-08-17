import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useActiveMembers, listMembers } from './members';
import { useAuthStore } from '@/store/authStore';

const MEMBERS = [
  { id: 'm1', name: 'Alice', phone: '9800000001', wallet_balance_paise: 5000, tier: 'BRONZE', is_active: true },
  { id: 'm2', name: 'Bob', phone: '9800000002', wallet_balance_paise: 3000, tier: 'SILVER', is_active: true },
  { id: 'm3', name: 'Carol', phone: '9800000003', wallet_balance_paise: 1000, tier: 'BRONZE', is_active: false },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('useActiveMembers', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok' }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('fetches and filters to active members only', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const { result } = renderHook(() => useActiveMembers(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.length).toBe(2);
    expect(result.current.data?.every(m => m.is_active)).toBe(true);
  });
});
