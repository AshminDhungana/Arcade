import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useToggleFlag } from './settings';
import { useFeatureFlags } from './featureFlags';
import { useFeatureFlagStore } from '@/store/featureFlagStore';

const BASE_FLAGS = {
  enable_members: false, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: false, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
};

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('useToggleFlag', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Stage the mock: first GET (mount) returns true so the store starts "on";
    // the PATCH + the invalidated refetch GET return false, so only the
    // mutation path can flip the store to false.
    let calls = 0;
    fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const isPatch = init?.method === 'PATCH';
      const enableMembers = isPatch || calls > 0 ? 'false' : 'true';
      calls += 1;
      return new Response(JSON.stringify({ ...BASE_FLAGS, enable_members: enableMembers }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);
    useFeatureFlagStore.getState().setFlags({ ...BASE_FLAGS, enable_members: true });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('patches the flag and syncs the store after the invalidated query refetches', async () => {
    const wrapper = makeWrapper();
    const { result } = renderHook(
      () => ({ toggle: useToggleFlag(), _flags: useFeatureFlags() }),
      { wrapper },
    );

    act(() => {
      result.current.toggle.mutate({ key: 'enable_members', value: false });
    });

    await waitFor(() =>
      expect(useFeatureFlagStore.getState().flags.enable_members).toBe(false),
    );
    // The mutation issued a PATCH to /api/settings (jsdom resolves the
    // relative URL against http://localhost, so match by substring + method).
    expect(
      fetchMock.mock.calls.some(
        (c) =>
          typeof c[0] === 'string' &&
          c[0].includes('/api/settings') &&
          (c[1] as RequestInit | undefined)?.method === 'PATCH',
      ),
    ).toBe(true);
  });
});
