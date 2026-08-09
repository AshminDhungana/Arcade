import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SeatGrid } from './SeatGrid';
import { SeatStatus } from '@/types/seat';
import type { ReactNode } from 'react';

const makeWrapper = () => {
  const qc = new QueryClient();
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
};

vi.mock('@/api/seats', () => ({
  useSeats: () => ({
    data: [
      { id: 's1', name: 'PC-01', zone_id: 'z1', zone_name: 'Floor A', mac_address: null, status: 'AVAILABLE', plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0, wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { id: 's2', name: 'PC-02', zone_id: 'z1', zone_name: 'Floor A', mac_address: null, status: SeatStatus.IN_USE, current_session_id: 'sess-2', plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0, wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { id: 's3', name: 'PC-03', zone_id: 'z1', zone_name: 'Floor A', mac_address: null, status: SeatStatus.MAINTENANCE, plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0, wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { id: 's4', name: 'PC-04', zone_id: 'z1', zone_name: 'Floor A', mac_address: null, status: SeatStatus.PAUSED, current_session_id: 'sess-4', plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0, wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    ],
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

vi.mock('./SessionDrawer', () => ({
  SessionDrawer: ({ seat }: { seat: { name: string } }) => <div data-testid="drawer">{seat.name}</div>,
}));

vi.mock('./SeatActionModal', () => ({
  SeatActionModal: ({ seat }: { seat: { name: string } }) => <div data-testid="modal">{seat.name}</div>,
}));

describe('SeatGrid', () => {
  it('groups seats by zone and renders them', () => {
    render(<SeatGrid />, { wrapper: makeWrapper() });
    const lists = screen.getAllByRole('list');
    expect(lists).toHaveLength(1);
    expect(screen.getByText('PC-01')).toBeInTheDocument();
    expect(screen.getByText('PC-02')).toBeInTheDocument();
    expect(screen.getByText('PC-03')).toBeInTheDocument();
    expect(screen.getByText('PC-04')).toBeInTheDocument();
    expect(screen.getByText('Floor A')).toBeInTheDocument();
  });

  it('opens the drawer for IN_USE seats', () => {
    render(<SeatGrid />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByText('PC-02'));
    expect(screen.getByTestId('drawer')).toHaveTextContent('PC-02');
  });

  it('opens the drawer for PAUSED seats', () => {
    render(<SeatGrid />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByText('PC-04'));
    expect(screen.getByTestId('drawer')).toHaveTextContent('PC-04');
  });

  it('opens the modal for AVAILABLE seats', () => {
    render(<SeatGrid />, { wrapper: makeWrapper() });
    fireEvent.click(screen.getByText('PC-01'));
    expect(screen.getByTestId('modal')).toHaveTextContent('PC-01');
  });
});
