import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type { ShiftCurrentResponse, ShiftResponse } from '@/types/shift';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export async function fetchCurrentShift(
  token: string | null,
): Promise<ShiftCurrentResponse | null> {
  const res = await fetch(`${API_BASE}/shifts/current`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Failed to load current shift: ${res.status}`);
  return (await res.json()) as ShiftCurrentResponse | null;
}

export async function openShift(token: string | null, floatPaise: number): Promise<ShiftResponse> {
  const res = await fetch(`${API_BASE}/shifts/open`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ float_paise: floatPaise }),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to open shift: ${res.status}`);
  }
  return (await res.json()) as ShiftResponse;
}

export async function closeShift(token: string | null, countedPaise: number): Promise<ShiftResponse> {
  const res = await fetch(`${API_BASE}/shifts/close`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ counted_paise: countedPaise }),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(err.detail ?? `Failed to close shift: ${res.status}`);
  }
  return (await res.json()) as ShiftResponse;
}

export function useCurrentShift() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['shifts', 'current'],
    queryFn: () => fetchCurrentShift(token),
    enabled: !!token,
    refetchInterval: 30_000,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });
}

export function useOpenShift() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (floatPaise: number) => openShift(token, floatPaise),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shifts', 'current'] });
    },
  });
}

export function useCloseShift() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (countedPaise: number) => closeShift(token, countedPaise),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shifts', 'current'] });
    },
  });
}
