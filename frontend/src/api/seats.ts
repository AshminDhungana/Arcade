import { useQuery } from '@tanstack/react-query';
import type { Seat } from '@/types/seat';

const API_BASE = '/api';

/** Fetch all seats from the backend. */
export async function fetchSeats(): Promise<Seat[]> {
  const res = await fetch(`${API_BASE}/seats`);
  if (!res.ok) {
    throw new Error(`Failed to fetch seats: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as Seat[];
}

/** Fetch a single seat by ID. */
export async function fetchSeat(seatId: string): Promise<Seat> {
  const res = await fetch(`${API_BASE}/seats/${seatId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch seat: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as Seat;
}

/** React Query hook for listing all seats.
 *  Invalidated automatically by `useWebSocket` on `seat_updated` events. */
export function useSeats() {
  return useQuery({
    queryKey: ['seats'],
    queryFn: fetchSeats,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

/** React Query hook for a single seat. */
export function useSeat(seatId: string) {
  return useQuery({
    queryKey: ['seat', seatId],
    queryFn: () => fetchSeat(seatId),
    enabled: seatId != null && seatId !== '',
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}
