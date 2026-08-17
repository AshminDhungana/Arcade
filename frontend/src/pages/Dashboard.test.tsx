import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import DashboardPage from './Dashboard';
import { useAuthStore } from '@/store/authStore';
import { bulkForceOverlay } from '@/api/seats';

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ status: 'connected' as const }),
}));

vi.mock('@/components/SeatGrid', () => ({
  SeatGrid: () => <div data-testid="seat-grid" />,
}));

vi.mock('@/components/UnprintedInvoices', () => ({
  UnprintedInvoices: () => <div data-testid="unprinted-invoices" />,
}));

vi.mock('@/components/ShiftModal', () => ({
  ShiftModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="shift-modal" /> : null,
}));

vi.mock('@/store/toastStore', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/api/seats', () => ({
  bulkForceOverlay: vi.fn(),
}));

import { useAlertStore } from '@/store/alertStore';

vi.mock('@/lib/chime', () => ({ playStaffAlertChime: vi.fn() }));

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/']}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe('DashboardPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'tok',
      staff: { id: 's1', name: 'Admin User', role: 'ADMIN', is_active: true },
      isAuthenticated: true,
    });
    useAlertStore.setState({ alerts: [] });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ accessToken: null, staff: null, isAuthenticated: false });
  });

  it('renders dashboard title and connection badge', () => {
    render(<DashboardPage />, { wrapper: makeWrapper() });
    expect(screen.getByText('Arcade Dashboard')).toBeInTheDocument();
    // Connection badge shows green dot when connected (no text label)
    expect(screen.getByLabelText('Connection status')).toBeInTheDocument();
    expect(screen.getByLabelText('Connection status')).toHaveClass('bg-success/15');
  });

  it('shows "Lock all idle seats" button for ADMIN users', () => {
    render(<DashboardPage />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /lock all idle seats/i })).toBeInTheDocument();
  });

  it('hides "Lock all idle seats" button for non-admin users', () => {
    useAuthStore.setState({
      accessToken: 'tok',
      staff: { id: 's2', name: 'Cashier User', role: 'CASHIER', is_active: true },
      isAuthenticated: true,
    });
    render(<DashboardPage />, { wrapper: makeWrapper() });
    expect(screen.queryByRole('button', { name: /lock all idle seats/i })).not.toBeInTheDocument();
  });

  it('calls bulkForceOverlay(true) when "Lock all idle seats" is clicked', async () => {
    vi.mocked(bulkForceOverlay).mockResolvedValue({ succeeded: ['seat-1'], failed: [] });
    render(<DashboardPage />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /lock all idle seats/i }));
    await waitFor(() => expect(bulkForceOverlay).toHaveBeenCalledWith(true));
  });

  it('shows the staff alert modal when an alert is queued', () => {
    useAlertStore.getState().push({
      type: 'STAFF_ALERT',
      seat_id: 'seat-1',
      message: 'Staff assistance requested',
      timestamp: '2026-08-08T10:00:00Z',
    });

    render(<DashboardPage />, { wrapper: makeWrapper() });

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveTextContent('Staff assistance requested');
    expect(dialog).toHaveTextContent('Seat: seat-1');
  });

  it('shows the Shift button and opens the shift modal', () => {
    render(<DashboardPage />, { wrapper: makeWrapper() });
    const shiftButton = screen.getByRole('button', { name: /shift/i });
    expect(shiftButton).toBeInTheDocument();
    expect(screen.queryByTestId('shift-modal')).not.toBeInTheDocument();
    fireEvent.click(shiftButton);
    expect(screen.getByTestId('shift-modal')).toBeInTheDocument();
  });

  describe('EventsWidget', () => {
    beforeEach(() => {
      vi.stubGlobal('fetch', vi.fn(async () =>
        new Response(JSON.stringify([
          { id: 'e1', name: 'FIFA Cup', game_title: 'FIFA 24', event_date: '2026-08-15T18:00:00Z', entry_fee_paise: 5000, prize_pool_paise: 20000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
          { id: 'e2', name: 'Past Event', game_title: 'Game', event_date: '2026-07-01T18:00:00Z', entry_fee_paise: 2000, prize_pool_paise: 5000, bracket_type: 'SINGLE_ELIMINATION', status: 'COMPLETED' },
        ]), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    });
    afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

    it('renders EventsWidget with upcoming events', async () => {
      render(<DashboardPage />, { wrapper: makeWrapper() });
      await waitFor(() => expect(screen.getByText('Upcoming Events')).toBeInTheDocument());
      // Wait for event data to load
      await waitFor(() => expect(screen.getByText('FIFA Cup')).toBeInTheDocument());
      expect(screen.queryByText('Past Event')).not.toBeInTheDocument();
      expect(screen.getByRole('link', { name: /view all/i })).toHaveAttribute('href', '/events');
    });
  });
});
