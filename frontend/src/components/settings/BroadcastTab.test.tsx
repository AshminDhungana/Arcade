import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BroadcastTab } from './BroadcastTab';
import { useAuthStore } from '@/store/authStore';
import type { ReactNode } from 'react';

const SETTINGS_WITH_BANNER: Record<string, string> = {
  event_banner: 'Weekend Tournament',
};

const SETTINGS_EMPTY: Record<string, string> = {};

const mockState = {
  settings: {} as Record<string, string>,
  patchFn: vi.fn(),
  isLoading: false,
  isError: false,
};

vi.mock('@/api/settings', () => ({
  useSettings: () => ({
    data: mockState.settings,
    isLoading: mockState.isLoading,
    isError: mockState.isError,
    refetch: vi.fn(),
  }),
  patchSettings: (patch: Record<string, string>) => mockState.patchFn(patch),
}));

vi.mock('@/store/toastStore', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('BroadcastTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
    mockState.settings = SETTINGS_WITH_BANNER;
    mockState.patchFn = vi.fn().mockResolvedValue({});
    mockState.isLoading = false;
    mockState.isError = false;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('seeds the field from settings.event_banner', () => {
    render(<BroadcastTab />, { wrapper: makeWrapper() });

    expect(screen.getByLabelText(/event banner/i)).toHaveValue('Weekend Tournament');
  });

  it('editing the field and clicking Save calls patchSettings with { event_banner: <typed value> } and shows success toast', async () => {
    mockState.settings = SETTINGS_EMPTY;
    render(<BroadcastTab />, { wrapper: makeWrapper() });

    const input = screen.getByLabelText(/event banner/i);
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Summer Sale' } });
    });

    const saveBtn = screen.getByRole('button', { name: /^save$/i });
    await act(async () => {
      await fireEvent.click(saveBtn);
    });

    await waitFor(() =>
      expect(mockState.patchFn).toHaveBeenCalledWith({ event_banner: 'Summer Sale' }),
    );

    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Event banner saved');
    });
  });

  it('empties the field when clearing and saving, and shows success toast', async () => {
    mockState.settings = SETTINGS_WITH_BANNER;
    render(<BroadcastTab />, { wrapper: makeWrapper() });

    const input = screen.getByLabelText(/event banner/i);
    await act(async () => {
      fireEvent.change(input, { target: { value: '' } });
    });

    const saveBtn = screen.getByRole('button', { name: /^save$/i });
    await act(async () => {
      await fireEvent.click(saveBtn);
    });

    await waitFor(() =>
      expect(mockState.patchFn).toHaveBeenCalledWith({ event_banner: '' }),
    );

    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Event banner saved');
    });
  });

  it('shows loading and error states', () => {
    // Test loading state
    mockState.isLoading = true;
    mockState.isError = false;

    const { unmount } = render(<BroadcastTab />, { wrapper: makeWrapper() });
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    unmount();

    // Test error state
    mockState.isLoading = false;
    mockState.isError = true;

    render(<BroadcastTab />, { wrapper: makeWrapper() });
    expect(screen.getByText(/failed to load broadcast settings/i)).toBeInTheDocument();
  });
});
