import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CommandsPanel } from './CommandsPanel';
import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';
import type { ReactNode } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useToastStore } from '@/store/toastStore';
import type { UseQueryResult } from '@tanstack/react-query';

vi.mock('@/api/seats', () => ({
  forceOverlay: vi.fn().mockResolvedValue(undefined),
  useSeat: vi.fn(),
}));

vi.mock('@/api/sessions', () => ({
  usePauseSession: vi.fn(),
  useResumeSession: vi.fn(),
}));

const { forceOverlay, useSeat } = await import('@/api/seats');
const { usePauseSession, useResumeSession } = await import('@/api/sessions');

const inUseSeat: Seat = {
  id: 'seat-1', name: 'PC-01', zone_id: 'zone-1', mac_address: null,
  status: SeatStatus.IN_USE, plug_id: null, is_console: false, notes: null,
  overlay_forced: false, assigned_end_at: null,
    maintenance_since: null,
    maintenance_duration_seconds: null, wol_attempts: 0, wol_successes: 0,
  wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z',
  current_session_id: 'sess-1',
};

function createMockQueryResult<T>(
  data: T | undefined,
  isLoading: boolean,
  isError: boolean,
  error: Error | null,
): UseQueryResult<T, Error> {
  return {
    data, isLoading, isError, error,
    isPending: isLoading,
    isSuccess: !isLoading && !isError && data !== undefined,
    isFetched: !isLoading,
    isFetching: false,
    isRefetching: false,
    isStale: false,
    status: isLoading ? 'pending' : (isError ? 'error' : 'success'),
    fetchStatus: 'idle',
    failureCount: 0,
    failureReason: null,
    refetch: vi.fn(),
    isLoadingError: isError && isLoading,
    isRefetchError: false,
    isPlaceholderData: false,
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: error ? Date.now() : 0,
    errorUpdateCount: error ? 1 : 0,
    fetchFailureCount: 0,
    fetchFailureReason: null,
  } as unknown as UseQueryResult<T, Error>;
}

const makeWrapper = () => {
  const qc = new QueryClient();
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

describe('CommandsPanel', () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: 'tok',
      staff: { id: 's1', name: 'Admin', role: 'ADMIN', is_active: true },
    });
    vi.mocked(usePauseSession).mockReturnValue({ mutate: vi.fn(), isPending: false } as never);
    vi.mocked(useResumeSession).mockReturnValue({ mutate: vi.fn(), isPending: false } as never);
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(inUseSeat, false, false, null));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders Pause Session for an IN_USE seat and pauses on click', () => {
    const pauseMutate = vi.fn();
    vi.mocked(usePauseSession).mockReturnValue({ mutate: pauseMutate, isPending: false } as never);
    render(<CommandsPanel seat={inUseSeat} sessionId="sess-1" />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /pause session/i }));
    expect(pauseMutate).toHaveBeenCalledWith({ session_id: 'sess-1' }, expect.any(Object));
  });

  it('renders Resume Session for a PAUSED seat and resumes on click', () => {
    const pausedSeat = { ...inUseSeat, status: SeatStatus.PAUSED };
    const resumeMutate = vi.fn();
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(pausedSeat, false, false, null));
    vi.mocked(useResumeSession).mockReturnValue({ mutate: resumeMutate, isPending: false } as never);
    render(<CommandsPanel seat={inUseSeat} sessionId="sess-1" />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /resume session/i }));
    expect(resumeMutate).toHaveBeenCalledWith({ session_id: 'sess-1' }, expect.any(Object));
  });

  it('uses live seat data from useSeat to flip the button', () => {
    const pausedSeat = { ...inUseSeat, status: SeatStatus.PAUSED };
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(pausedSeat, false, false, null));
    render(<CommandsPanel seat={inUseSeat} sessionId="sess-1" />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /resume session/i })).toBeInTheDocument();
  });

  it('disables the timer button when the seat has no in-flight session', () => {
    vi.mocked(useSeat).mockReturnValue(
      createMockQueryResult({ ...inUseSeat, status: SeatStatus.AVAILABLE }, false, false, null),
    );
    render(<CommandsPanel seat={inUseSeat} sessionId="sess-1" />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /pause session/i })).toBeDisabled();
  });

  it('shows overlay controls for admins and calls forceOverlay', async () => {
    render(<CommandsPanel seat={inUseSeat} sessionId="sess-1" />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /force overlay on/i }));
    await waitFor(() => expect(forceOverlay).toHaveBeenCalledWith('seat-1', true));
    fireEvent.click(screen.getByRole('button', { name: /force overlay off/i }));
    await waitFor(() => expect(forceOverlay).toHaveBeenCalledWith('seat-1', false));
  });

  it('hides overlay controls for cashiers', () => {
    useAuthStore.setState({
      accessToken: 'tok',
      staff: { id: 's2', name: 'Cashier', role: 'CASHIER', is_active: true },
    });
    render(<CommandsPanel seat={inUseSeat} sessionId="sess-1" />, { wrapper: makeWrapper() });
    expect(screen.queryByRole('button', { name: /force overlay/i })).not.toBeInTheDocument();
  });

  it('shows an error toast when pause fails', async () => {
    const pushSpy = vi.spyOn(useToastStore.getState(), 'push');
    const pauseMutate = vi.fn(
      (_vars: unknown, opts: { onError: (err: Error) => void }) =>
        opts.onError(new Error('Expected status ACTIVE to pause')),
    );
    vi.mocked(usePauseSession).mockReturnValue({ mutate: pauseMutate, isPending: false } as never);
    render(<CommandsPanel seat={inUseSeat} sessionId="sess-1" />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /pause session/i }));
    await waitFor(() =>
      expect(pushSpy).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'error', message: 'Expected status ACTIVE to pause' }),
      ),
    );
    pushSpy.mockRestore();
  });
});
