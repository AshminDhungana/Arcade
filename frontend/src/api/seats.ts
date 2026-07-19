import { useQuery } from '@tanstack/react-query';
import type { Seat } from '@/types/seat';
import { useAuthStore } from '@/store/authStore';

const API_BASE = '/api';

/** Build request headers, attaching the bearer token when one is available.
 *  Mirrors the established pattern in members.ts / invoices.ts / sessions.ts. */
function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

/** Fetch all seats from the backend (requires cashier+ auth). */
export async function fetchSeats(): Promise<Seat[]> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_BASE}/seats`, { headers: authHeaders(token) });
  if (!res.ok) {
    throw new Error(`Failed to fetch seats: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as Seat[];
}

/** Fetch a single seat by ID (requires cashier+ auth). */
export async function fetchSeat(seatId: string): Promise<Seat> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_BASE}/seats/${seatId}`, { headers: authHeaders(token) });
  if (!res.ok) {
    throw new Error(`Failed to fetch seat: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as Seat;
}

/** Generate a one-time enroll code for a seat.
 *  The backend mints a short-lived code used by the agent to self-enroll. */
export async function generateEnrollCode(seatId: string): Promise<{ code: string; expires_at: string }> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_BASE}/seats/${seatId}/enroll-code`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to generate enroll code: ${res.status}`);
  return res.json();
}

/** Regenerate the override PIN for a seat.
 *  The backend mints a fresh 6-digit PIN and returns it once. */
export async function regenerateOverridePin(seatId: string): Promise<{ override_pin: string }> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_BASE}/seats/${seatId}/override-pin`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to regenerate override PIN: ${res.status}`);
  return res.json();
}

/** Force a seat's kiosk overlay ON/OFF.
 *  POST /api/seats/{id}/overlay
 *  Requires admin privilege (backend enforces). Returns 204 on success. */
export async function forceOverlay(seatId: string, show: boolean): Promise<void> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_BASE}/seats/${seatId}/overlay`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ show }),
  });
  if (!res.ok) {
    throw new Error(`Failed to force overlay: ${res.status} ${res.statusText}`);
  }
}

/** Bulk force overlay for all AVAILABLE seats (show=true) or all overlay_forced seats (show=false).
 *  POST /api/seats/bulk/overlay
 *  Requires admin privilege. Returns { succeeded: string[], failed: {seat_id, detail}[] }. */
export async function bulkForceOverlay(show: boolean): Promise<{
  succeeded: string[];
  failed: { seat_id: string; detail: string }[];
}> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_BASE}/seats/bulk/overlay`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ show }),
  });
  if (!res.ok) {
    throw new Error(`Failed to bulk force overlay: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as {
    succeeded: string[];
    failed: { seat_id: string; detail: string }[];
  };
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
