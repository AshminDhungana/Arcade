import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SettingsPage from './Settings';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { Staff } from '@/types/settings';

const STAFF_ADMIN: Staff = {
  id: 's1',
  name: 'Admin User',
  role: 'ADMIN',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockState = {
  staff: [STAFF_ADMIN] as Staff[],
  createStaffFn: vi.fn(),
  deactivateStaffFn: vi.fn(),
  reactivateStaffFn: vi.fn(),
  changeStaffPinFn: vi.fn(),
};

const isPendingRefs = {
  createStaff: { current: false },
  deactivateStaff: { current: false },
  reactivateStaff: { current: false },
  changeStaff: { current: false },
};

vi.mock('@/api/settings', () => ({
  useStaff: () => ({
    data: mockState.staff,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateStaff: () => ({
    mutateAsync: mockState.createStaffFn,
    get isPending() {
      return isPendingRefs.createStaff.current;
    },
  }),
  useDeactivateStaff: () => ({
    mutateAsync: mockState.deactivateStaffFn,
    get isPending() {
      return isPendingRefs.deactivateStaff.current;
    },
  }),
  useReactivateStaff: () => ({
    mutateAsync: mockState.reactivateStaffFn,
    get isPending() {
      return isPendingRefs.reactivateStaff.current;
    },
  }),
  useChangeStaffPin: () => ({
    mutateAsync: mockState.changeStaffPinFn,
    get isPending() {
      return isPendingRefs.changeStaff.current;
    },
  }),
  useToggleFlag: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  patchSettings: vi.fn(),
}));

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
        require_print_before_release: false,
        enable_assigned_time_limit: false,
      },
    });
    mockState.staff = [STAFF_ADMIN];
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

  it('switches to Staff tab when clicking the Staff tab button', async () => {
    renderWithProviders(<SettingsPage />);

    // Click the Staff tab
    const staffTab = screen.getByRole('tab', { name: 'Staff' });
    await userEvent.click(staffTab);

    // Staff tab should be selected
    expect(screen.getByRole('tab', { name: 'Staff', selected: true })).toBeInTheDocument();

    // Staff panel should show the staff table (not the coming soon stub)
    expect(screen.getByText('Admin User')).toBeInTheDocument();
    expect(screen.getByText('ADMIN')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add staff/i })).toBeInTheDocument();

    // Feature Flags panel should no longer be visible
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
  });
});
