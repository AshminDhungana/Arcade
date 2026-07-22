import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import App from './App';
import { useAuthStore } from './store/authStore';
import { useFeatureFlagStore } from './store/featureFlagStore';
import { useThemeStore } from './store/themeStore';

// Mock the heavy page modules so these tests exercise routing only
// (their data hooks would otherwise hit the network).
vi.mock('./pages/Members', () => ({
  MembersPage: () => <div>Members Page</div>,
}));
vi.mock('./pages/Settings', () => ({
  default: () => <div>Settings Page</div>,
}));
vi.mock('./pages/Events', () => ({
  EventsPage: () => <div>Events Page</div>,
}));

const ALL_ON = {
  enable_members: true, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: true, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
  require_print_before_release: false, enable_assigned_time_limit: false,
};

const createWrapper = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { staleTime: Infinity } },
  });
  return ({ children }: { children: ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </BrowserRouter>
  );
};

describe('App', () => {
  beforeEach(() => {
    // Authenticate so ProtectedRoute renders its children instead of redirecting
    useAuthStore.setState({ isAuthenticated: true });
    // Seed flags as loaded + members/tournaments on so guarded routes render
    useFeatureFlagStore.getState().setFlags(ALL_ON);
    vi.clearAllMocks();
  });

  it('initializes theme store on mount', () => {
    const mockToggle = vi.spyOn(useThemeStore.getState(), 'initialize');
    window.history.pushState({}, '', '/login');
    render(<App />, { wrapper: createWrapper() });
    expect(mockToggle).toHaveBeenCalled();
  });

  it('renders login page at /login', () => {
    window.history.pushState({}, '', '/login');
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('routes /members to the Members page', () => {
    window.history.pushState({}, '', '/members');
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByText('Members Page')).toBeInTheDocument();
  });

  it('routes /settings to the Settings page', () => {
    window.history.pushState({}, '', '/settings');
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByText('Settings Page')).toBeInTheDocument();
  });

  it('shows FeatureUnavailable at /members when enable_members is off', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_ON, enable_members: false });
    window.history.pushState({}, '', '/members');
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByText(/is unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText('Members Page')).not.toBeInTheDocument();
  });

  it('routes /events to the Events page when enable_tournaments is on', () => {
    window.history.pushState({}, '', '/events');
    render(<App />, { wrapper: createWrapper() });
    expect(screen.getByText('Events Page')).toBeInTheDocument();
  });
});
