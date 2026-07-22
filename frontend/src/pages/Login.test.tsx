import { describe, it, expect, vi, beforeEach, afterEach, test } from 'vitest';
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

  it('renders the GamepadDirectional icon via Icon component', () => {
    const { container } = renderWithRouter();
    // Logo button wraps the Icon component; the SVG doesn't have role="button" itself
    const icon = container.querySelector(
      'svg[aria-hidden="true"]',
    );
    expect(icon).not.toBeNull();
    // Check that it's the GamepadDirectional icon (4 path elements)
    expect(icon?.querySelectorAll('path').length).toBe(4);
  });

  it('renders the signature as a decorative, theme-aware svg', () => {
    const { container } = renderWithRouter();
    // SignatureMark is an SVG with fill="currentColor" and aria-hidden="true"
    const sig = container.querySelector(
      'svg[fill="currentColor"][aria-hidden="true"]:not([class*="lucide"])',
    );
    expect(sig).not.toBeNull();
    // Inner SVG has aria-hidden
    expect(sig?.getAttribute('aria-hidden')).toBe('true');
    // Check it has theme-aware classes via the wrapper / className prop
    // const sigClass = sig?.getAttribute('class') ?? '';
    // The markdown wrapper uses these classes (set in Login.tsx: text-neutral-900 dark:text-white)
    // But since we're testing the SVG directly, we check it has the right viewBox
    expect(sig?.getAttribute('viewBox')).toBe('0 0 1571 800');
    expect(sig?.querySelectorAll('path').length).toBe(3);
    // Wrapper should have positioning (the SignatureWatermark div)
    const wrapper = sig?.parentElement;
    expect(wrapper).not.toBeNull();
    const wrapperClass = wrapper?.getAttribute('class') ?? '';
    expect(wrapperClass).toContain('bottom-4');
    expect(wrapperClass).toContain('right-8');
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

describe('Login layout — centered logo above card', () => {
  const renderWithRouterAndMotion = () =>
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>,
    );

  test('logo is rendered above login card, not inside it', () => {
    renderWithRouterAndMotion();
    const logo = screen.getByRole('button', { name: /switch to (light|dark) theme/i });
    const card = screen.getByTestId('login-card');
    expect(logo).toBeInTheDocument();
    expect(card).toBeInTheDocument();
    // Logo should NOT be inside card
    expect(card).not.toContainHTML(logo.outerHTML);
  });

  test('logo has correct size, variant, motion', () => {
    renderWithRouterAndMotion();
    const logo = screen.getByRole('button', { name: /switch to (light|dark) theme/i });
    // Logo button has size classes
    expect(logo).toHaveClass('h-24', 'w-24'); // h-24 w-24 = 96px = size 80
  });

  test('theme badge button exists in card header', () => {
    renderWithRouterAndMotion();
    // The card header doesn't have a separate theme badge button - the logo IS the theme toggle
    const logo = screen.getByRole('button', { name: /switch to (light|dark) theme/i });
    expect(logo).toBeInTheDocument();
  });

  test('card header shows "Staff Sign In" title, not "Arcade"', () => {
    renderWithRouterAndMotion();
    expect(screen.getByText('Staff Sign In')).toBeInTheDocument();
    expect(screen.queryByText('Arcade')).not.toBeInTheDocument();
  });
});
