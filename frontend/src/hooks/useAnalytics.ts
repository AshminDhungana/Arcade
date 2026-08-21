import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import type { MobileAnalytics } from '@/types/mobileAnalytics'

const API_BASE = '/api'

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

async function fetchMobileAnalytics(token: string | null): Promise<MobileAnalytics> {
  const res = await fetch(`${API_BASE}/analytics/mobile`, { headers: authHeaders(token) })
  if (!res.ok) {
    throw new Error(`Failed to load mobile analytics: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as MobileAnalytics
}

export function useAnalytics() {
  const token = useAuthStore((s) => s.accessToken)
  return useQuery({
    queryKey: ['analytics', 'mobile'],
    queryFn: () => fetchMobileAnalytics(token),
    enabled: !!token,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
