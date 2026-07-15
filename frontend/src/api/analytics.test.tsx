import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { fetchAnalyticsSummary, useAnalyticsSummary } from './analytics';
import { useAuthStore } from '@/store/authStore';
import type { AnalyticsSummary } from '@/types/analytics';

const SAMPLE: AnalyticsSummary = {
  total_revenue_paise: 5000,
  session_count: 1,
  average_duration_seconds: 3600,
  busiest_hour: { hour: 15, session_count: 3 },
  weekly_revenue: [{ date: '2026-07-15', total_paise: 5000 }],
  top_pos_items: [{ menu_item_id: 'm1', name: 'Tea', quantity: 3 }],
  zone_utilisation: [{ zone_id: 'z1', zone_name: 'Zone A', session_hours: 2, available_hours: 24, utilisation_pct: 8.33 }],
  member_registration_trend: [{ date: '2026-07-15', count: 2 }],
  member_stats: { new_today: 1, active_last_30d: 1, top_spenders: [] },
  health_alerts: [],
  upcoming_reservations: [],
  wol_success_rates: [],
  current_shift_id: null,
  shift_opened_at: null,
};

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('analytics API client', () => {
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

  it('fetchAnalyticsSummary hits /api/analytics/summary with Bearer token', async () => {
    const res = await fetchAnalyticsSummary('tok');
    expect(res.total_revenue_paise).toBe(5000);
    expect(res.member_registration_trend).toHaveLength(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/analytics/summary');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });

  it('useAnalyticsSummary returns the summary', async () => {
    const { result } = renderHook(() => useAnalyticsSummary(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.session_count).toBe(1);
  });
});
