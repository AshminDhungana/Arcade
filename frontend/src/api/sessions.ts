// frontend/src/api/sessions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type { SessionResponse } from '@/types/session';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/** Fetch session detail for checkout preview. */
export async function fetchSession(
  sessionId: string,
  token: string | null,
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch session: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SessionResponse;
}

/** Hook to fetch session detail for checkout. */
export function useSession(sessionId: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchSession(sessionId, token),
    enabled: !!sessionId && !!token,
    refetchOnWindowFocus: false,
  });
}

/** Start a new session on a seat. */
export async function startSession(
  body: { seat_id: string; member_id: string | null },
  token: string | null,
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Failed to start session: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SessionResponse;
}

/** Hook to start a session. */
export function useStartSession() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { seat_id: string; member_id: string | null }) => startSession(body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['seats'] }),
  });
}
