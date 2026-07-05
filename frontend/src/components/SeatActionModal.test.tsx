import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SeatActionModal } from './SeatActionModal';
import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';

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

describe('SeatActionModal', () => {
  it('renders seat name and close button', () => {
    const onClose = vi.fn();
    render(<SeatActionModal seat={mockSeat} onClose={onClose} />);
    expect(screen.getByText('PC-01')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<SeatActionModal seat={mockSeat} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText('Close modal'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('displays seat notes when available', () => {
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />);
    expect(screen.getByTestId('seat-notes')).toBeInTheDocument();
  });

  it('shows Start Session button for AVAILABLE seats', () => {
    render(<SeatActionModal seat={mockSeat} onClose={() => {}} />);
    expect(screen.getByText('Start Session')).toBeInTheDocument();
  });

  it('shows Pause Session button for IN_USE seats', () => {
    const inUseSeat = { ...mockSeat, status: SeatStatus.IN_USE };
    render(<SeatActionModal seat={inUseSeat} onClose={() => {}} />);
    expect(screen.getByText('Pause Session')).toBeInTheDocument();
  });
});
