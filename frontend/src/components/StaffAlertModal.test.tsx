import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { StaffAlertModal } from './StaffAlertModal';
import { useAlertStore } from '@/store/alertStore';
import type { Seat } from '@/types/seat';

vi.mock('@/lib/chime', () => ({ playStaffAlertChime: vi.fn() }));

const wrapper = (client: QueryClient) =>
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };

const pushAlert = (seatId: string, message = 'Staff assistance requested') => {
  act(() => {
    useAlertStore.getState().push({
      type: 'STAFF_ALERT',
      seat_id: seatId,
      message,
      timestamp: '2026-08-08T10:00:00Z',
    });
  });
};

describe('StaffAlertModal', () => {
  beforeEach(() => {
    useAlertStore.setState({ alerts: [] });
  });

  it('renders nothing when the queue is empty', () => {
    render(<StaffAlertModal />, { wrapper: wrapper(new QueryClient()) });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows the head alert with the seat name resolved from the seats cache', () => {
    const client = new QueryClient();
    client.setQueryData<Seat[]>(['seats'], [
      { id: 'seat-1', name: 'Seat 3', status: 'AVAILABLE' } as Seat,
    ]);
    render(<StaffAlertModal />, { wrapper: wrapper(client) });

    pushAlert('seat-1');
    expect(screen.getByRole('dialog')).toHaveTextContent('Staff assistance requested');
    expect(screen.getByRole('dialog')).toHaveTextContent('Seat 3');
  });

  it('falls back to the raw seat_id when the seat is not in the cache', () => {
    render(<StaffAlertModal />, { wrapper: wrapper(new QueryClient()) });

    pushAlert('seat-unknown');
    expect(screen.getByRole('dialog')).toHaveTextContent('seat-unknown');
  });

  it('shows a waiting count and reveals the next alert on dismiss', () => {
    render(<StaffAlertModal />, { wrapper: wrapper(new QueryClient()) });

    pushAlert('seat-1');
    pushAlert('seat-2');
    expect(screen.getByRole('dialog')).toHaveTextContent('1 more waiting');

    fireEvent.click(screen.getByRole('button', { name: /ok, got it/i }));
    expect(screen.getByRole('dialog')).toHaveTextContent('Seat: seat-2');
    expect(screen.queryByText('1 more waiting')).not.toBeInTheDocument();
  });
});
