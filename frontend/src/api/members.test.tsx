import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { useMembers, listMembers } from './members';
import { useAuthStore } from '@/store/authStore';

const SAMPLE = [
  { id: 'm1', name: 'John', phone: '9800000001' },
  { id: 'm2', name: 'Jane', phone: '9800000002' },
];

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('members API client', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    fetchMock = vi.fn(
      async (_url: string) =>
        new Response(JSON.stringify(SAMPLE), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    );
    vi.stubGlobal('fetch', fetchMock);
    useAuthStore.setState({ accessToken: 'tok' });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('listMembers hits /api/members with default pagination and returns Member[]', async () => {
    const res = await listMembers({}, 'tok');
    expect(res).toHaveLength(2);
    expect(res[0].name).toBe('John');
    const [url] = fetchMock.mock.calls[0] as [string, ...unknown[]];
    expect(url).toContain('/api/members?');
    expect(url).toContain('q=');
    expect(url).toContain('limit=50');
    expect(url).toContain('offset=0');
  });

  it('useMembers hook returns members for a query', async () => {
    const wrapper = makeWrapper();
    const { result } = renderHook(() => useMembers(''), { wrapper });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data).toHaveLength(2);
  });
});
