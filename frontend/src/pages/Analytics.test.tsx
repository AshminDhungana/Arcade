import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { AnalyticsPage } from './Analytics';
import { useAuthStore } from '@/store/authStore';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { AnalyticsSummary } from '@/types/analytics';
import type { Seat } from '@/types/seat';
import { SeatStatus } from '@/types/seat';

const ALL_FLAGS = {
  enable_members: false, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: false, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
};

const SUMMARY: AnalyticsSummary = {
  total_revenue_paise: 25050,
  session_count: 12,
  average_duration_seconds: 4980,
  busiest_hour: { hour: 15, session_count: 3 },
  weekly_revenue: [
    { date: '2026-07-13', total_paise: 10000 },
    { date: '2026-07-14', total_paise: 20000 },
    { date: '2026-07-15', total_paise: 5000 },
  ],
  top_pos_items: [{ menu_item_id: 'm1', name: 'Tea', quantity: 3 }],
  zone_utilisation: [{ zone_id: 'z1', zone_name: 'Zone A', session_hours: 2, available_hours: 24, utilisation_pct: 8.33 }],
  member_registration_trend: [{ date: '2026-07-15', count: 2 }],
  member_stats: { new_today: 1, active_last_30d: 1, top_spenders: [] },
  health_alerts: [{ seat_id: 's1', seat_name: 'PC-01', reasons: ['cpu_temp_red'] }],
  upcoming_reservations: [],
  wol_success_rates: [],
  current_shift_id: null,
  shift_opened_at: null,
};

const SEATS: Seat[] = [
  {
    id: 's1', name: 'PC-01', zone_id: 'z', mac_address: null, status: SeatStatus.AVAILABLE,
    plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0,
    wol_failures: 0, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 's2', name: 'PC-02', zone_id: 'z', mac_address: null, status: SeatStatus.OFFLINE,
    plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0,
    wol_failures: 0, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('AnalyticsPage', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const isSeats = url.includes('/api/seats');
        const body = isSeats ? SEATS : SUMMARY;
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }),
    );
    useAuthStore.setState({ accessToken: 'tok' });
    // HealthAlerts is gated; seed the flag on so existing assertions hold.
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, enable_health_monitoring: true });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders KPIs, charts, and merged health alerts from a single column layout', async () => {
    const { container } = render(<AnalyticsPage />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Rs. 250.50')).toBeInTheDocument());

    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('1h 23m')).toBeInTheDocument();
    expect(screen.getByText('3 PM')).toBeInTheDocument();

    // Chart cards are exposed as images with descriptive labels.
    expect(screen.getByRole('img', { name: /weekly revenue bar chart/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /seat utilisation/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /top point-of-sale/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /member registration trend/i })).toBeInTheDocument();

    // Health alerts merge summary (overheating) + offline seat from /api/seats.
    expect(screen.getByText(/Overheating: PC-01/)).toBeInTheDocument();
    expect(screen.getByText(/Offline: PC-02/)).toBeInTheDocument();

    // Mobile-first: root grids collapse to a single column at 375px.
    expect(container.querySelector('[class*="grid-cols-1"]')).not.toBeNull();
  });

  it('hides HealthAlerts when enable_health_monitoring is off', async () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, enable_health_monitoring: false });
    render(<AnalyticsPage />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.queryByText(/health alert/i)).not.toBeInTheDocument(),
    );
  });

  it('shows HealthAlerts when enable_health_monitoring is on', async () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, enable_health_monitoring: true });
    render(<AnalyticsPage />, { wrapper: makeWrapper() });
    await waitFor(() =>
      expect(screen.getByText(/health alert/i)).toBeInTheDocument(),
    );
  });
});
