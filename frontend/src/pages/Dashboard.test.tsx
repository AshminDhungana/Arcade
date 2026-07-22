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

vi.mock('@/store/toastStore', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/api/seats', () => ({
  bulkForceOverlay: vi.fn(),
}));

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
});
