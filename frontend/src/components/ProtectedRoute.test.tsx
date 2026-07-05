import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';
import { useAuthStore } from '@/store/authStore';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      accessToken: null,
      staff: null,
      isAuthenticated: false,
    });
  });

  it('renders children when authenticated', () => {
    useAuthStore.setState({
      accessToken: 'mock-token',
      staff: { id: 'STAFF-001', name: 'Alice', role: 'ADMIN', is_active: true },
      isAuthenticated: true,
    });
    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div data-testid="protected">Secret</div>
        </ProtectedRoute>
      </BrowserRouter>,
    );
    expect(screen.getByTestId('protected')).toBeInTheDocument();
  });

  it('redirects when not authenticated', () => {
    useAuthStore.setState({
      accessToken: null,
      staff: null,
      isAuthenticated: false,
    });
    render(
      <BrowserRouter>
        <ProtectedRoute>
          <div data-testid="protected">Secret</div>
        </ProtectedRoute>
      </BrowserRouter>,
    );
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
  });
});
