import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useToggleFlag, useChangeStaffPin } from './settings';
import { useFeatureFlags } from './featureFlags';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useAuthStore } from '@/store/authStore';

const BASE_FLAGS = {
  enable_members: false, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: false, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
  require_print_before_release: false, enable_assigned_time_limit: false,
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
      const body: Record<string, string> = {};
      for (const [k, v] of Object.entries({ ...BASE_FLAGS, enable_members: enableMembers === 'true' })) {
        body[k] = String(v).toLowerCase();
      }
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);
    useFeatureFlagStore.getState().setFlags({ ...BASE_FLAGS, enable_members: true });
    // The feature-flags query is gated on an auth token (enabled: !!token),
    // so it only fires and syncs the store when authenticated. Establish that
    // precondition here, otherwise the invalidated refetch never runs and the
    // store stays at its seed value.
    useAuthStore.getState().login('test-token', {
      id: 'admin',
      name: 'Administrator',
      role: 'ADMIN',
      is_active: true,
    });
  });

  afterEach(() => {
    useAuthStore.getState().logout();
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

describe('useChangeStaffPin', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'admin', name: 'Administrator', role: 'ADMIN', is_active: true }),
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('PATCHes the new pin and invalidates the staff list', async () => {
    const invalidate = vi.fn();
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    qc.invalidateQueries = invalidate as never;

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useChangeStaffPin(), { wrapper });
    await result.current.mutateAsync({ id: 'admin', pin: 'newpin123' });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/staff/admin/pin'),
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ pin: 'newpin123' }) }),
    );
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['staff'] }));
  });
});
