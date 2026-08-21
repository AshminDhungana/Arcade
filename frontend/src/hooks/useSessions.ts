import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import type { MobileSession } from '@/types/mobileAnalytics'

const API_BASE = '/api'

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

async function fetchSessions(token: string | null): Promise<MobileSession[]> {
  const res = await fetch(`${API_BASE}/sessions`, { headers: authHeaders(token) })
  if (!res.ok) {
    throw new Error(`Failed to load sessions: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as MobileSession[]
}

export function useSessions() {
  const token = useAuthStore((s) => s.accessToken)
  return useQuery({
    queryKey: ['sessions'],
    queryFn: () => fetchSessions(token),
    enabled: !!token,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
}
