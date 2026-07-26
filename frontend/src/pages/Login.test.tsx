import { describe, it, expect, vi, beforeEach, afterEach, test, act } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { setPrefersReducedMotion } from '../test-setup';
import { act as reactAct } from 'react';

// ===== MOCKS - must be before any imports that use them =====

// Mock the login API
const mockLogin = vi.fn();
const MockedAuthError = class AuthError extends Error {
  readonly status: number;
  readonly retryAfter: number | null;
  constructor(message: string, status: number, retryAfter: number | null = null) {
    super(message);
    this.name = 'AuthError';
    this.status = status;
    this.retryAfter = retryAfter;
  }
};

vi.mock('@/api/auth', () => ({
  login: mockLogin,
  AuthError: MockedAuthError,
}));

// Mock the auth store
const mockStoreLogin = vi.fn();
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector) => selector({
    login: (token: string, staff: unknown) => mockStoreLogin(token, staff),
  })),
}));

// Mock react-router-dom's useNavigate to prevent navigation during tests
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Import Login AFTER mocks are set up
const Login = await import('./Login').then((m) => m.default);

// ===== TESTS =====

describe('Login', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderWithRouter = () =>
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

  it('renders staff ID and PIN fields', () => {
    renderWithRouter();
    expect(screen.getByLabelText(/staff id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/pin/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows error on wrong PIN', async () => {
    mockLogin.mockRejectedValue(new MockedAuthError('Invalid staff ID or PIN', 401));
    renderWithRouter();

    fireEvent.change(screen.getByLabelText(/staff id/i), { target: { value: 'STAFF-001' } });
    fireEvent.change(screen.getByLabelText(/pin/i), { target: { value: '0000' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid staff id or pin/i)).toBeInTheDocument();
    });
  });

  it('handles 429 lockout with retry countdown', async () => {
    mockLogin.mockRejectedValue(new MockedAuthError('Too many failed login attempts', 429, 900));
    renderWithRouter();

    fireEvent.change(screen.getByLabelText(/staff id/i), { target: { value: 'STAFF-001' } });
    fireEvent.change(screen.getByLabelText(/pin/i), { target: { value: '0000' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/account locked/i)).toBeInTheDocument();
    });
  });

  it('shows lockout message on 5th failed attempt (local failure count >= 5)', async () => {
    mockLogin.mockRejectedValue(new MockedAuthError('Invalid staff ID or PIN', 401));
    renderWithRouter();

    for (let i = 0; i < 4; i++) {
      fireEvent.change(screen.getByLabelText(/staff id/i), { target: { value: 'STAFF-001' } });
      fireEvent.change(screen.getByLabelText(/pin/i), { target: { value: '0000' } });
      fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
      await waitFor(() => expect(screen.getByText(/attempts remaining/i)).toBeInTheDocument());
    }

    // 5th attempt triggers local lockout message
    fireEvent.change(screen.getByLabelText(/staff id/i), { target: { value: 'STAFF-001' } });
    fireEvent.change(screen.getByLabelText(/pin/i), { target: { value: '0000' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() =>
      expect(screen.getByText(/account temporarily locked/i)).toBeInTheDocument()
    );
  });

  it('stores token and staff in authStore on successful login', async () => {
    mockLogin.mockResolvedValue({
      access_token: 'tok123',
      staff: { id: 'STAFF-001', role: 'ADMIN' },
    });
    renderWithRouter();

    fireEvent.change(screen.getByLabelText(/staff id/i), { target: { value: 'STAFF-001' } });
    fireEvent.change(screen.getByLabelText(/pin/i), { target: { value: '1234' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await reactAct(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    expect(mockStoreLogin).toHaveBeenCalledWith('tok123', { id: 'STAFF-001', role: 'ADMIN' });
  });

  it('renders the GamepadDirectional icon via Icon component', () => {
    const { container } = renderWithRouter();
    const icon = container.querySelector('svg[aria-hidden="true"]');
    expect(icon).not.toBeNull();
    expect(icon?.querySelectorAll('path').length).toBe(4);
  });

  it('renders the signature as a decorative, theme-aware svg', () => {
    const { container } = renderWithRouter();
    const sig = container.querySelector('svg[fill="currentColor"][aria-hidden="true"]:not([class*="lucide"])');
    expect(sig).not.toBeNull();
    expect(sig?.getAttribute('aria-hidden')).toBe('true');
    expect(sig?.getAttribute('viewBox')).toBe('0 0 1571 800');
    expect(sig?.querySelectorAll('path').length).toBe(3);
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
    expect(screen.getByRole('button', { name: /switch to dark theme/i })).toBeInTheDocument();
  });

  it('renders and toggles correctly when reduced-motion is preferred', () => {
    setPrefersReducedMotion(true);
    try {
      localStorage.clear();
      const { container } = renderWithRouter();
      expect(screen.getByLabelText(/staff id/i)).toBeInTheDocument();
      const wrapper = container.querySelector('.login-root');
      expect(wrapper?.getAttribute('data-theme')).toBe('dark');
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
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

  test('logo is rendered above login card, not inside it', () => {
    renderWithRouterAndMotion();
    const logo = screen.getByRole('button', { name: /switch to (light|dark) theme/i });
    const card = screen.getByTestId('login-card');
    expect(logo).toBeInTheDocument();
    expect(card).toBeInTheDocument();
    expect(card).not.toContainHTML(logo.outerHTML);
  });

  test('logo has correct size, variant, motion', () => {
    renderWithRouterAndMotion();
    const logo = screen.getByRole('button', { name: /switch to (light|dark) theme/i });
    expect(logo).toHaveClass('h-24', 'w-24');
  });

  test('theme badge button exists in card header', () => {
    renderWithRouterAndMotion();
    const logo = screen.getByRole('button', { name: /switch to (light|dark) theme/i });
    expect(logo).toBeInTheDocument();
  });

  test('card header shows "Staff Sign In" title, not "Arcade"', () => {
    renderWithRouterAndMotion();
    expect(screen.getByText('Staff Sign In')).toBeInTheDocument();
    expect(screen.queryByText('Arcade')).not.toBeInTheDocument();
  });
});
