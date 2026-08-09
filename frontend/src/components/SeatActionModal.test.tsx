import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SeatActionModal } from './SeatActionModal';
import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';
import type { ReactNode } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { Member } from '@/types/members';
import type { UseQueryResult } from '@tanstack/react-query';

const ALL_FLAGS = {
  enable_members: false, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: false, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
  require_print_before_release: false, enable_assigned_time_limit: false,
};

const MEMBER: Member = {
  id: 'm1',
  name: 'John',
  phone: '9800000001',
  birth_month: null,
  wallet_balance_paise: 0,
  loyalty_points: 0,
  tier: 'BRONZE',
  total_visits: 0,
  total_seconds_played: 0,
  created_at: '',
  updated_at: '',
};

let lastMutate: (...args: unknown[]) => void;

vi.mock('@/api/sessions', () => ({
  useStartSession: () => ({ mutate: (...a: unknown[]) => lastMutate(...a), isPending: false }),
}));

vi.mock('@/components/MemberSearch', () => ({
  MemberSearch: ({ onSelect }: { onSelect: (m: Member) => void }) => (
    <button type="button" onClick={() => onSelect(MEMBER)}>pick member</button>
  ),
}));

vi.mock('@/api/seats', () => ({
  forceOverlay: vi.fn().mockResolvedValue(undefined),
  generateEnrollCode: vi.fn().mockResolvedValue({ code: 'TEST123', expires_at: '2024-01-01T00:00:00Z' }),
  regenerateOverridePin: vi.fn().mockResolvedValue({ override_pin: '123456' }),
  useSeat: vi.fn(),
}));

const { forceOverlay } = await import('@/api/seats');
const { useSeat } = await import('@/api/seats');

// Helper to create a mock UseQueryResult
function createMockQueryResult<T>(
  data: T | undefined,
  isLoading: boolean,
  isError: boolean,
  error: Error | null
): UseQueryResult<T, Error> {
  return {
    data,
    isLoading,
    isError,
    error,
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

const mockSeat: Seat = {
  id: 'seat-1',
  name: 'PC-01',
  zone_id: 'zone-1',
  mac_address: null,
  status: SeatStatus.AVAILABLE,
  plug_id: null,
  is_console: false,
  notes: 'Test note',
  wol_attempts: 0,
  wol_successes: 0,
  wol_failures: 0,
  overlay_forced: false,
  assigned_end_at: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const makeWrapper = () => {
  const qc = new QueryClient();
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

describe('SeatActionModal', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'tok' });
    lastMutate = vi.fn();
    // Default mock for useSeat - returns the prop seat as data
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(mockSeat, false, false, null));
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders seat name and close button', () => {
    const onClose = vi.fn();
    render(<SeatActionModal seat={mockSeat} onClose={onClose} />, { wrapper: makeWrapper() });
    expect(screen.getByText('PC-01')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<SeatActionModal seat={mockSeat} onClose={onClose} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByLabelText('Close modal'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('displays seat notes when available', () => {
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByTestId('seat-notes')).toBeInTheDocument();
  });

  it('shows Start Session button for AVAILABLE seats', () => {
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByText('Start Session')).toBeInTheDocument();
  });

  it('selecting a member and starting posts seat_id + member_id', () => {
    const startSpy = vi.fn();
    lastMutate = startSpy;
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByText('pick member'));
    fireEvent.click(screen.getByText('Start Session'));
    expect(startSpy).toHaveBeenCalledWith(
      expect.objectContaining({ seat_id: 'seat-1', member_id: 'm1' }),
      expect.any(Object),
    );
  });

  it('allows starting a session without a member when flag is off', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, require_member_for_session: false });
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /start session/i })).toBeEnabled();
  });

  it('disables Start Session without a member when flag is on', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, require_member_for_session: true });
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /start session/i })).toBeDisabled();
  });

  it('shows Force Overlay On/Off buttons for all seat statuses', () => {
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /force overlay on/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /force overlay off/i })).toBeInTheDocument();
  });

  it('calls forceOverlay(seatId, true) when Force Overlay On is clicked', async () => {
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /force overlay on/i }));
    await waitFor(() => expect(forceOverlay).toHaveBeenCalledWith('seat-1', true));
  });

  it('calls forceOverlay(seatId, false) when Force Overlay Off is clicked', async () => {
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /force overlay off/i }));
    await waitFor(() => expect(forceOverlay).toHaveBeenCalledWith('seat-1', false));
  });

  it('disables Force Overlay buttons while request is pending', async () => {
    let resolveFn: (value: void | PromiseLike<void>) => void;
    vi.mocked(forceOverlay).mockImplementation(() => new Promise((resolve) => { resolveFn = resolve; }));
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /force overlay on/i }));
    expect(screen.getByRole('button', { name: /force overlay on/i })).toBeDisabled();
    resolveFn!(undefined);
    await waitFor(() => expect(screen.getByRole('button', { name: /force overlay on/i })).toBeEnabled());
  });

  it('hides assign-time field when flag off', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, enable_assigned_time_limit: false });
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.queryByLabelText(/assign time limit/i)).not.toBeInTheDocument();
  });

  it('shows assign-time field and forwards it when flag on', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, enable_assigned_time_limit: true });
    lastMutate = vi.fn();
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });

    const input = screen.getByLabelText(/assign time limit/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: '120' } });
    fireEvent.click(screen.getByText('Start Session'));

    expect(lastMutate).toHaveBeenCalledWith(
      { seat_id: 'seat-1', member_id: null, assigned_minutes: 120 },
      expect.any(Object),
    );
  });
});

describe('SeatActionModal auto-update', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ accessToken: 'tok' });
  });

  it('uses useSeat hook with seat.id and initialData from prop', () => {
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(mockSeat, false, false, null));

    render(<SeatActionModal seat={mockSeat} onClose={vi.fn()} />, { wrapper: makeWrapper() });

    expect(vi.mocked(useSeat)).toHaveBeenCalledWith('seat-1', { initialData: mockSeat });
  });

  it('renders seat data from useSeat hook when status updates', () => {
    const updatedSeat = { ...mockSeat, status: SeatStatus.IN_USE };
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(updatedSeat, false, false, null));

    render(<SeatActionModal seat={mockSeat} onClose={vi.fn()} />, { wrapper: makeWrapper() });

    expect(screen.getByText('IN USE')).toBeInTheDocument();
  });

  it('falls back to prop data when useSeat returns error', () => {
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult<Seat>(undefined, false, true, new Error('Not found')));

    render(<SeatActionModal seat={mockSeat} onClose={vi.fn()} />, { wrapper: makeWrapper() });

    // Should still render using initialData/prop data
    expect(screen.getByText('PC-01')).toBeInTheDocument();
    expect(screen.getByText('AVAILABLE')).toBeInTheDocument();
  });

  it('renders immediately with initialData while useSeat is loading', () => {
    vi.mocked(useSeat).mockReturnValue(createMockQueryResult(mockSeat, true, false, null));

    render(<SeatActionModal seat={mockSeat} onClose={vi.fn()} />, { wrapper: makeWrapper() });

    // initialData should render immediately, no loading spinner for the seat data itself
    expect(screen.getByText('PC-01')).toBeInTheDocument();
  });
});
