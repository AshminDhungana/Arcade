import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FeatureFlagsTab } from './FeatureFlagsTab';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useAuthStore } from '@/store/authStore';
import type { ReactNode } from 'react';
import type { Mock } from 'vitest';

let mutateFn: Mock;
const isPendingRef = { current: false };

vi.mock('@/api/settings', () => ({
  useToggleFlag: () => ({
    mutate: (...args: unknown[]) => mutateFn(...args),
    get isPending() {
      return isPendingRef.current;
    },
  }),
  patchSettings: vi.fn(),
}));

vi.mock('@/store/toastStore', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const makeWrapper = () => {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

describe('FeatureFlagsTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
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
      },
    });
    mutateFn = vi.fn();
    isPendingRef.current = false;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders all 10 feature flags with labels and descriptions', () => {
    render(<FeatureFlagsTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByText('Show the Members management surface')).toBeInTheDocument();
    expect(screen.getByText('Packages')).toBeInTheDocument();
    expect(screen.getByText('Enable Packages and pricing management')).toBeInTheDocument();
    expect(screen.getByText('Point of Sale')).toBeInTheDocument();
    expect(screen.getByText('Enable POS sales and billing')).toBeInTheDocument();
    expect(screen.getByText('Inventory')).toBeInTheDocument();
    expect(screen.getByText('Enable inventory tracking')).toBeInTheDocument();
    expect(screen.getByText('Reservations')).toBeInTheDocument();
    expect(screen.getByText('Enable seat reservations')).toBeInTheDocument();
    expect(screen.getByText('Vouchers')).toBeInTheDocument();
    expect(screen.getByText('Enable voucher codes and promotions')).toBeInTheDocument();
    expect(screen.getByText('Tournaments')).toBeInTheDocument();
    expect(screen.getByText('Enable tournament management')).toBeInTheDocument();
    expect(screen.getByText('Expense Tracking')).toBeInTheDocument();
    expect(screen.getByText('Enable expense tracking and reports')).toBeInTheDocument();
    expect(screen.getByText('Health Monitoring')).toBeInTheDocument();
    expect(screen.getByText('Enable agent health monitoring')).toBeInTheDocument();
    expect(screen.getByText('Require Member for Session')).toBeInTheDocument();
    expect(screen.getByText('Require a member to start a session')).toBeInTheDocument();
  });

  it('renders a Switch for each flag reflecting current store value', () => {
    render(<FeatureFlagsTab />, { wrapper: makeWrapper() });

    const switches = screen.getAllByRole('switch');
    expect(switches).toHaveLength(10);

    switches.forEach((sw) => {
      expect(sw).not.toBeChecked();
    });
  });

  it('toggling a switch calls useToggleFlag mutation with key and new value', () => {
    render(<FeatureFlagsTab />, { wrapper: makeWrapper() });

    const membersSwitch = screen.getByRole('switch', { name: /members/i });
    fireEvent.click(membersSwitch);

    expect(mutateFn).toHaveBeenCalledWith(
      { key: 'enable_members', value: true },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      })
    );
  });

  it('shows success toast when toggle mutation succeeds', async () => {
    render(<FeatureFlagsTab />, { wrapper: makeWrapper() });

    const membersSwitch = screen.getByRole('switch', { name: /members/i });
    fireEvent.click(membersSwitch);

    // Get the onSuccess callback and invoke it
    const callArgs = mutateFn.mock.calls[0];
    const options = callArgs[1];
    await waitFor(() => {
      options.onSuccess?.();
    });

    const { toast } = await import('@/store/toastStore');
    expect(toast.success).toHaveBeenCalledWith('Members enabled');
  });

  it('shows error toast when toggle mutation fails', async () => {
    render(<FeatureFlagsTab />, { wrapper: makeWrapper() });

    const membersSwitch = screen.getByRole('switch', { name: /members/i });
    fireEvent.click(membersSwitch);

    const callArgs = mutateFn.mock.calls[0];
    const options = callArgs[1];
    await waitFor(() => {
      options.onError?.(new Error('Network error'));
    });

    const { toast } = await import('@/store/toastStore');
    expect(toast.error).toHaveBeenCalledWith('Failed to toggle Members: Network error');
  });

  it('disables switches while mutation is pending', () => {
    isPendingRef.current = true;

    render(<FeatureFlagsTab />, { wrapper: makeWrapper() });

    const switches = screen.getAllByRole('switch');
    switches.forEach((sw) => {
      expect(sw).toBeDisabled();
    });
  });

  it('shows saving indicator while any mutation is pending', () => {
    isPendingRef.current = true;

    render(<FeatureFlagsTab />, { wrapper: makeWrapper() });

    expect(screen.getByText(/saving/i)).toBeInTheDocument();
  });
});
