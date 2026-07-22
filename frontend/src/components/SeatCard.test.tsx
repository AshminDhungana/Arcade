import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SeatCard } from './SeatCard';
import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';
import type { ReactNode } from 'react';

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
  overlay_forced: false, // base seat
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

const withLimit = (over: Partial<Seat>): Seat => ({
  ...mockSeat,
  assigned_end_at: '2024-01-01T01:00:00Z',
  current_session_id: 'sess-1',
  ...over,
});

describe('SeatCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders seat name and status', () => {
    render(<SeatCard seat={mockSeat} onClick={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByText('PC-01')).toBeInTheDocument();
    expect(screen.getByLabelText('Seat status: AVAILABLE')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<SeatCard seat={mockSeat} onClick={handleClick} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledWith(mockSeat);
  });

  it('renders as a PC by default', () => {
    render(<SeatCard seat={mockSeat} onClick={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByText('PC')).toBeInTheDocument();
  });

  it('renders as Console when is_console is true', () => {
    const consoleSeat = { ...mockSeat, is_console: true };
    render(<SeatCard seat={consoleSeat} onClick={() => {}} />, { wrapper: makeWrapper() });
    expect(screen.getByText('Console')).toBeInTheDocument();
  });

  it('shows lock badge when overlay_forced is true', () => {
    const forcedSeat = { ...mockSeat, overlay_forced: true };
    render(<SeatCard seat={forcedSeat} onClick={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.getByRole('img', { name: /lock/i })).toBeInTheDocument();
  });

  it('does not show lock badge when overlay_forced is false', () => {
    render(<SeatCard seat={mockSeat} onClick={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.queryByRole('img', { name: /lock/i })).not.toBeInTheDocument();
  });

  // --- Epic 6.5.4: "Add time" control ---

  it('hides Add time for an AVAILABLE seat', () => {
    render(<SeatCard seat={mockSeat} onClick={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.queryByRole('button', { name: /add time/i })).not.toBeInTheDocument();
  });

  it('hides Add time for an IN_USE seat without an assigned limit', () => {
    const seat = withLimit({ status: SeatStatus.IN_USE, assigned_end_at: null });
    render(<SeatCard seat={seat} onClick={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.queryByRole('button', { name: /add time/i })).not.toBeInTheDocument();
  });

  it('shows Add time for an IN_USE seat with an assigned limit', () => {
    const seat = withLimit({ status: SeatStatus.IN_USE });
    render(<SeatCard seat={seat} onClick={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /add time/i })).toBeInTheDocument();
  });

  it('shows Add time for an EXPIRED seat with an assigned limit', () => {
    const seat = withLimit({ status: SeatStatus.EXPIRED });
    render(<SeatCard seat={seat} onClick={vi.fn()} />, { wrapper: makeWrapper() });
    expect(screen.getByRole('button', { name: /add time/i })).toBeInTheDocument();
  });

  it('does not open the seat modal when Add time is clicked and calls extend', async () => {
    const handleClick = vi.fn();
    const seat = withLimit({ status: SeatStatus.IN_USE });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sess-1' }),
    } as Response);
    window.prompt = vi.fn(() => '30');

    render(<SeatCard seat={seat} onClick={handleClick} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /add time/i }));

    expect(window.prompt).toHaveBeenCalled();
    expect(handleClick).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/sessions/sess-1/extend',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ additional_minutes: 30 }),
        }),
      ),
    );
  });

  it('does not extend when prompt is cancelled', () => {
    const seat = withLimit({ status: SeatStatus.IN_USE });
    globalThis.fetch = vi.fn();
    window.prompt = vi.fn(() => null);

    render(<SeatCard seat={seat} onClick={vi.fn()} />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByRole('button', { name: /add time/i }));

    expect(window.prompt).toHaveBeenCalled();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });
});
