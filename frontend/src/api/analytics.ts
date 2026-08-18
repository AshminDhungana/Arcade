import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type { AnalyticsSummary, PLSummary, PLMonthParams } from '@/types/analytics';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export async function fetchAnalyticsSummary(token: string | null): Promise<AnalyticsSummary> {
  const res = await fetch(`${API_BASE}/analytics/summary`, { headers: authHeaders(token) });
  if (!res.ok) {
    throw new Error(`Failed to load analytics: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as AnalyticsSummary;
}

export function useAnalyticsSummary() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: () => fetchAnalyticsSummary(token),
    enabled: !!token,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export async function fetchPLSummary(
  token: string | null,
  start?: string,
  end?: string
): Promise<PLSummary> {
  const params = new URLSearchParams();
  if (start) params.set('start', start);
  if (end) params.set('end', end);
  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/reports/pl/summary${query}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to load P&L summary: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as PLSummary;
}

export async function fetchPLMonthly(
  token: string | null,
  params: PLMonthParams
): Promise<PLSummary> {
  const res = await fetch(
    `${API_BASE}/reports/pl/monthly/${params.year}/${params.month}`,
    { headers: authHeaders(token) }
  );
  if (!res.ok) {
    throw new Error(`Failed to load monthly P&L: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as PLSummary;
}

export function usePLSummary(start?: string, end?: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['analytics', 'pl', 'summary', start, end],
    queryFn: () => fetchPLSummary(token, start, end),
    enabled: !!token,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function usePLMonthly(params: PLMonthParams) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['analytics', 'pl', 'monthly', params.year, params.month],
    queryFn: () => fetchPLMonthly(token, params),
    enabled: !!token,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}
