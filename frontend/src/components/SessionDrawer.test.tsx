import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionDrawer } from './SessionDrawer';
import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';
import type { ReactNode } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { UseQueryResult } from '@tanstack/react-query';

vi.mock('./pos/POSPanel', () => ({ POSPanel: () => <div data-testid="pos-panel" /> }));
vi.mock('./invoice/CheckoutPanel', () => ({ CheckoutPanel: () => <div data-testid="checkout-panel" /> }));
vi.mock('@/api/seats', () => ({
  useSeat: vi.fn(),
  forceOverlay: vi.fn(),
}));
vi.mock('@/api/sessions', () => ({
  usePauseSession: () => ({ mutate: vi.fn(), isPending: false }),
  useResumeSession: () => ({ mutate: vi.fn(), isPending: false }),
}));

const { useSeat } = await import('@/api/seats');

const inUseSeat: Seat = {
  id: 'seat-1', name: 'PC-01', zone_id: 'zone-1', mac_address: null,
  status: SeatStatus.IN_USE, plug_id: null, is_console: false, notes: null,
  overlay_forced: false, assigned_end_at: null,
    maintenance_since: null,
    maintenance_duration_seconds: null, wol_attempts: 0, wol_successes: 0,
  wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
  current_session_id: 'sess-1',
};

function createMockQueryResult<T>(
  data: T | undefined,
  isLoading: boolean,
  isError: boolean,
  error: Error | null,
): UseQueryResult<T, Error> {
  return {
    data, isLoading, isError, error,
    isPending: isLoading,
    isSuccess: !isLoading && !isError && data !== undefined,
    isFetched: !isLoading,
    isFetching: false,
    isRefetching: false,
    isStale: false,
    status: isLoading ? 'pending' : (isError ? 'error' : 'success'),
    fetchStatus: 'idle',
    failureCount: 0,
    failureReason: null,
    refetch: vi.fn(),
    isLoadingError: isError && isLoading,
    isRefetchError: false,
    isPlaceholderData: false,
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: error ? Date.now() : 0,
    errorUpdateCount: error ? 1 : 0,
    fetchFailureCount: 0,
    fetchFailureReason: null,
  } as unknown as UseQueryResult<T, Error>;
}

const makeWrapper = () => {
  const qc = new QueryClient();
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

describe('SessionDrawer', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'tok',
      staff: { id: 's1', name: 'Admin', role: 'ADMIN', is_active: true },
    });
    useFeatureFlagStore.setState({
      flags: {
        enable_members: false,
        enable_packages: false,
        enable_pos: false,
        enable_inventory: false,
        enable_reservations: false,
        enable_vouchers: false,
        enable_tournaments: false,
        enable_expense_tracking: false,
        enable_health_monitoring: false,
        require_member_for_session: false,
        enable_tuya: false,
        require_print_before_release: false,
        block_shift_close_unprinted: false,
        overlay_pauses_billing: false,
        enable_assigned_time_limit: false,
        enable_wake_on_lan: false,
        enable_remote_commands: false,
        enable_analytics: false,
        enable_promotions: false,
        enable_loyalty_discounts: false,
        enable_maintenance_mode: false,
        enable_kiosk_branding: false,
        enable_audit_export: false,
        agent_auto_start: false,
        shift_cash_variance_threshold: 5000,
      },
    });
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(inUseSeat, false, false, null));
  });

  it('shows Checkout as the default tab when POS is disabled', () => {
    render(<SessionDrawer seat={inUseSeat} sessionId="sess-1" onClose={vi.fn()} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByTestId('checkout-panel')).toBeInTheDocument();
  });

  it('renders the Commands tab with pause control', () => {
    render(<SessionDrawer seat={inUseSeat} sessionId="sess-1" onClose={vi.fn()} />, {
      wrapper: makeWrapper(),
    });
    fireEvent.click(screen.getByRole('tab', { name: /commands/i }));
    expect(screen.getByRole('button', { name: /pause session/i })).toBeInTheDocument();
  });

  it('shows "Session active" in the header for an IN_USE seat', () => {
    render(<SessionDrawer seat={inUseSeat} sessionId="sess-1" onClose={vi.fn()} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByText(/Session active/)).toBeInTheDocument();
  });

  it('shows "Session paused" in the header when the live seat is PAUSED', () => {
    vi.mocked(useSeat).mockReturnValue(
      createMockQueryResult({ ...inUseSeat, status: SeatStatus.PAUSED }, false, false, null),
    );
    render(<SessionDrawer seat={inUseSeat} sessionId="sess-1" onClose={vi.fn()} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByText(/Session paused/)).toBeInTheDocument();
  });
});
