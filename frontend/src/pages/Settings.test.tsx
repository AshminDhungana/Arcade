import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SettingsPage from './Settings';

const renderWithProviders = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

    // Feature Flags panel should be visible
    expect(screen.getByText('Feature Flags panel — coming soon in Task 27')).toBeInTheDocument();
  });

  it('switches to Staff tab when clicking the Staff tab button', () => {
    renderWithProviders(<SettingsPage />);

    // Click the Staff tab
    const staffTab = screen.getByRole('tab', { name: 'Staff' });
    fireEvent.click(staffTab);

    // Staff tab should be selected
    expect(screen.getByRole('tab', { name: 'Staff', selected: true })).toBeInTheDocument();

    // Staff panel should be visible
    expect(screen.getByText('Staff panel — coming soon in Task 30')).toBeInTheDocument();

    // Feature Flags panel should no longer be visible
    expect(screen.queryByText('Feature Flags panel — coming soon in Task 27')).not.toBeInTheDocument();
  });
});
