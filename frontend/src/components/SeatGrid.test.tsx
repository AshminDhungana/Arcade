import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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

// Mock the API hook
vi.mock('@/api/seats', () => ({
  useSeats: () => ({
    data: [
      { id: 's1', name: 'PC-01', zone_id: 'z1', mac_address: null, status: 'AVAILABLE', plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0, wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { id: 's2', name: 'PC-02', zone_id: 'z1', mac_address: null, status: SeatStatus.IN_USE, plug_id: null, is_console: false, notes: null, wol_attempts: 0, wol_successes: 0, wol_failures: 0, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    ],
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

describe('SeatGrid', () => {
  it('renders all seats from the query', () => {
    render(<SeatGrid />, { wrapper: makeWrapper() });
    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.getByText('PC-01')).toBeInTheDocument();
    expect(screen.getByText('PC-02')).toBeInTheDocument();
  });

  it('is accessible with aria-label', () => {
    render(<SeatGrid />, { wrapper: makeWrapper() });
    expect(screen.getByLabelText('Seat grid')).toBeInTheDocument();
  });
});
