import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from './Login';

// Mock the login API
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  AuthError: class AuthError extends Error {
    readonly status: number;
    readonly retryAfter: number | null;
    constructor(message: string, status: number, retryAfter: number | null = null) {
      super(message);
      this.name = 'AuthError';
      this.status = status;
      this.retryAfter = retryAfter;
    }
  },
}));
// eslint-disable-next-line import/first
import { login, AuthError as MockedAuthError } from '@/api/auth';

// Mock the auth store
const mockStoreLogin = vi.fn();
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    login: (token: string, staff: unknown) => mockStoreLogin(token, staff),
  })),
}));

describe('Login', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderWithRouter = () =>
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>,
    );

  it('renders staff ID and PIN fields', () => {
    renderWithRouter();
    expect(screen.getByLabelText(/staff id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/pin/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows error on wrong PIN', async () => {
    (login as ReturnType<typeof vi.fn>).mockRejectedValue(
      new MockedAuthError('Invalid staff ID or PIN', 401),
    );
    renderWithRouter();

    fireEvent.change(screen.getByLabelText(/staff id/i), {
      target: { value: 'STAFF-001' },
    });
    fireEvent.change(screen.getByLabelText(/pin/i), {
      target: { value: '0000' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid staff id or pin/i)).toBeInTheDocument();
    });
  });

  it('handles 429 lockout with retry countdown', async () => {
    (login as ReturnType<typeof vi.fn>).mockRejectedValue(
      new MockedAuthError('Too many failed login attempts', 429, 900),
    );
    renderWithRouter();

    fireEvent.change(screen.getByLabelText(/staff id/i), {
      target: { value: 'STAFF-001' },
    });
    fireEvent.change(screen.getByLabelText(/pin/i), {
      target: { value: '0000' },
    });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/account locked/i)).toBeInTheDocument();
    });
  });
});
