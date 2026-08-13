import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
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
});
