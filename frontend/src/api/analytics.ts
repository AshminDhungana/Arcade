import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type { AnalyticsSummary } from '@/types/analytics';

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
