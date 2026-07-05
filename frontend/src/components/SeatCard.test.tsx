import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SeatCard } from './SeatCard';
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
  notes: null,
  wol_attempts: 0,
  wol_successes: 0,
  wol_failures: 0,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('SeatCard', () => {
  it('renders seat name and status', () => {
    render(<SeatCard seat={mockSeat} onClick={() => {}} />);
    expect(screen.getByText('PC-01')).toBeInTheDocument();
    expect(screen.getByLabelText('Seat status: AVAILABLE')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<SeatCard seat={mockSeat} onClick={handleClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledWith(mockSeat);
  });

  it('renders as a PC by default', () => {
    render(<SeatCard seat={mockSeat} onClick={() => {}} />);
    expect(screen.getByText('PC')).toBeInTheDocument();
  });

  it('renders as Console when is_console is true', () => {
    const consoleSeat = { ...mockSeat, is_console: true };
    render(<SeatCard seat={consoleSeat} onClick={() => {}} />);
    expect(screen.getByText('Console')).toBeInTheDocument();
  });
});
