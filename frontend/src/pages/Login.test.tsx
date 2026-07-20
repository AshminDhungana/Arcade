import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from './Login';
import { setPrefersReducedMotion } from '../test-setup';

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

  it('renders the gamepad tile brand image without a gradient wrapper', () => {
    const { container } = renderWithRouter();
    const img = container.querySelector('img[src="/arcade_icon.svg"]');
    expect(img).not.toBeNull();
    expect(img?.className).toContain('rounded-2xl');
    expect(document.querySelector('.bg-brand-gradient')).toBeNull();
  });

  it('renders the signature as a decorative, theme-aware svg', () => {
    const { container } = renderWithRouter();
    // Signature is the only svg that fills with currentColor (lucide icons use fill="none")
    const sig = container.querySelector('svg[fill="currentColor"]');
    expect(sig).not.toBeNull();
    expect(sig?.getAttribute('aria-hidden')).toBe('true');
    const classAttr = sig?.getAttribute('class') ?? '';
    expect(classAttr).toContain('text-foreground');
    expect(classAttr).toContain('bottom-4');
    expect(classAttr).toContain('right-4');
    expect(sig?.querySelectorAll('path').length).toBe(3);
  });

  it('toggles theme via the logo button and persists the choice', () => {
    localStorage.clear();
    const { container } = renderWithRouter();
    const wrapper = container.querySelector('.login-root');
    expect(wrapper).not.toBeNull();
    expect(wrapper?.getAttribute('data-theme')).toBe('dark');

    const toggle = screen.getByRole('button', { name: /switch to light theme/i });
    fireEvent.click(toggle);

    expect(wrapper?.getAttribute('data-theme')).toBe('light');
    expect(localStorage.getItem('arcade-login-theme')).toBe('light');
    expect(
      screen.getByRole('button', { name: /switch to dark theme/i }),
    ).toBeInTheDocument();
  });

  it('renders and toggles correctly when reduced-motion is preferred', () => {
    // Turns useReducedMotion() on so the reduced-motion branches in Login
    // (initial={false}, exit={undefined}) actually execute during this render.
    setPrefersReducedMotion(true);
    try {
      localStorage.clear();
      const { container } = renderWithRouter();
      // Core UI still renders with animations disabled.
      expect(screen.getByLabelText(/staff id/i)).toBeInTheDocument();
      const wrapper = container.querySelector('.login-root');
      expect(wrapper?.getAttribute('data-theme')).toBe('dark');
      // Toggle still works under reduced motion (exercises the exit branch).
      fireEvent.click(screen.getByRole('button', { name: /switch to light theme/i }));
      expect(wrapper?.getAttribute('data-theme')).toBe('light');
    } finally {
      setPrefersReducedMotion(false);
    }
  });
});
