import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import App from './App';
import { useAuthStore } from './store/authStore';

// Mock the heavy page modules so these tests exercise routing only
// (their data hooks would otherwise hit the network).
vi.mock('./pages/Members', () => ({
  MembersPage: () => <div>Members Page</div>,
}));
vi.mock('./pages/Settings', () => ({
  default: () => <div>Settings Page</div>,
}));

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
    vi.clearAllMocks();
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
});
