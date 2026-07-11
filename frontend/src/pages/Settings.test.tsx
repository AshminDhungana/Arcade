import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SettingsPage from './Settings';
import { useFeatureFlagStore } from '@/store/featureFlagStore';

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the Settings page with default "Feature Flags" tab active', () => {
    renderWithProviders(<SettingsPage />);

    // Header should be present
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument();

    // Tab rail should show 6 tabs
    expect(screen.getByRole('tab', { name: 'Feature Flags' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Pricing' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Schedules' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Staff' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Menu' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Printer' })).toBeInTheDocument();

    // Feature Flags tab should be selected by default
    expect(screen.getByRole('tab', { name: 'Feature Flags', selected: true })).toBeInTheDocument();

    // Feature Flags panel should show the flags list (not the old stub)
    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByText('Show the Members management surface')).toBeInTheDocument();
  });

  it('switches to Staff tab when clicking the Staff tab button', () => {
    renderWithProviders(<SettingsPage />);

    // Click the Staff tab
    const staffTab = screen.getByRole('tab', { name: 'Staff' });
    fireEvent.click(staffTab);

    // Staff tab should be selected
    expect(screen.getByRole('tab', { name: 'Staff', selected: true })).toBeInTheDocument();

    // Staff panel should be visible (still shows coming soon)
    expect(screen.getByText('Staff panel — coming soon in Task 30')).toBeInTheDocument();

    // Feature Flags panel should no longer be visible
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
  });
});
