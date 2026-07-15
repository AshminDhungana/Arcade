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

/** Generate a one-time enroll code for a seat.
 *  The backend mints a short-lived code used by the agent to self-enroll. */
export async function generateEnrollCode(seatId: string): Promise<{ code: string; expires_at: string }> {
  const res = await fetch(`${API_BASE}/seats/${seatId}/enroll-code`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to generate enroll code: ${res.status}`);
  return res.json();
}

/** Regenerate the override PIN for a seat.
 *  The backend mints a fresh 6-digit PIN and returns it once. */
export async function regenerateOverridePin(seatId: string): Promise<{ override_pin: string }> {
  const res = await fetch(`${API_BASE}/seats/${seatId}/override-pin`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to regenerate override PIN: ${res.status}`);
  return res.json();
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
