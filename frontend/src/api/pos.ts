import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { MenuItem, SessionPOSItem } from '@/types/pos';
import { useAuthStore } from '@/store/authStore';

const API_BASE = '/api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ---------------------------------------------------------------------------
// Fetch functions
// ---------------------------------------------------------------------------

/** Fetch all menu items for POS display. */
export async function fetchMenu(token: string | null): Promise<MenuItem[]> {
  const res = await fetch(`${API_BASE}/pos/menu`, { headers: authHeaders(token) });
  if (!res.ok) {
    throw new Error(`Failed to fetch menu: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as MenuItem[];
}

/** Fetch all POS items for a given session. */
export async function fetchSessionItems(
  sessionId: string,
  token: string | null,
): Promise<SessionPOSItem[]> {
  const res = await fetch(`${API_BASE}/pos/items/${sessionId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch session items: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SessionPOSItem[];
}

/** Add a POS item to a session. */
export async function addPosItem(
  body: { session_id: string; menu_item_id: string; quantity: number },
  token: string | null,
): Promise<SessionPOSItem> {
  const res = await fetch(`${API_BASE}/pos/items`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to add item' }));
    throw new Error(err.detail ?? `Failed to add item: ${res.status}`);
  }
  return (await res.json()) as SessionPOSItem;
}

/** Remove a POS item from a session. */
export async function removePosItem(
  posItemId: string,
  sessionId: string,
  token: string | null,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/pos/items/${posItemId}?session_id=${sessionId}`,
    {
      method: 'DELETE',
      headers: authHeaders(token),
    },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to remove item' }));
    throw new Error(err.detail ?? `Failed to remove item: ${res.status}`);
  }
}

// ---------------------------------------------------------------------------
// React Query hooks
// ---------------------------------------------------------------------------

/** Hook to fetch all menu items. Caches for 5 minutes. */
export function useMenu() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['menu'],
    queryFn: () => fetchMenu(token),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

/** Hook to fetch POS items for a specific session. */
export function useSessionItems(sessionId: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['sessionItems', sessionId],
    queryFn: () => fetchSessionItems(sessionId, token),
    enabled: !!sessionId,
    refetchOnWindowFocus: false,
  });
}

/** Mutation hook to add an item to a session.
 *  Invalidates the session items cache on success. */
export function useAddPosItem() {
  const token = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: { session_id: string; menu_item_id: string; quantity: number }) =>
      addPosItem(body, token),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['sessionItems', variables.session_id],
      });
      // Also invalidate menu to refresh stock counts
      queryClient.invalidateQueries({ queryKey: ['menu'] });
    },
  });
}

/** Mutation hook to remove a POS item from a session.
 *  Invalidates the session items cache on success. */
export function useRemovePosItem() {
  const token = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (args: { posItemId: string; sessionId: string }) =>
      removePosItem(args.posItemId, args.sessionId, token),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['sessionItems', variables.sessionId],
      });
      queryClient.invalidateQueries({ queryKey: ['menu'] });
    },
  });
}
