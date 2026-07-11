import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SeatActionModal } from './SeatActionModal';
import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';
import type { ReactNode } from 'react';
import { useAuthStore } from '@/store/authStore';
import type { Member } from '@/types/members';

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

let lastMutate: (...args: any[]) => void;

vi.mock('@/api/sessions', () => ({
  useStartSession: () => ({ mutate: (...a: any[]) => lastMutate(...a), isPending: false }),
}));

vi.mock('@/components/MemberSearch', () => ({
  MemberSearch: ({ onSelect }: { onSelect: (m: Member) => void }) => (
    <button type="button" onClick={() => onSelect(MEMBER)}>pick member</button>
  ),
}));

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

  it('shows Pause Session button for IN_USE seats', () => {
    const inUseSeat = { ...mockSeat, status: SeatStatus.IN_USE };
    render(<SeatActionModal seat={inUseSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByText('Pause Session')).toBeInTheDocument();
  });

  it('selecting a member and starting posts seat_id + member_id', () => {
    const startSpy = vi.fn();
    lastMutate = startSpy;
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByText('pick member'));
    fireEvent.click(screen.getByText('Start Session'));
    expect(startSpy).toHaveBeenCalledWith(
      { seat_id: 'seat-1', member_id: 'm1' },
      expect.any(Object),
    );
  });
});
