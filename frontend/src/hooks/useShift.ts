import { useQuery, useMutation } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'

const API_BASE = '/api'

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export interface MobileShiftData {
  isOpen: boolean
  shift: { id: string; openedAt: string; openedBy: string } | null
  summary: MobileShiftSummary
}

export interface MobileShiftSummary {
  revenue: number
  sessions: number
  avgDuration: number
  posRevenue: number
}

async function fetchShift(token: string | null): Promise<MobileShiftData> {
  const res = await fetch(`${API_BASE}/shifts/current`, { headers: authHeaders(token) })
  if (!res.ok) {
    throw new Error(`Failed to load shift: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as MobileShiftData
}

async function openShift(token: string | null): Promise<MobileShiftData> {
  const res = await fetch(`${API_BASE}/shifts/open`, { method: 'POST', headers: authHeaders(token) })
  if (!res.ok) {
    throw new Error(`Failed to open shift: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as MobileShiftData
}

async function closeShift(token: string | null): Promise<MobileShiftData> {
  const res = await fetch(`${API_BASE}/shifts/close`, { method: 'POST', headers: authHeaders(token) })
  if (!res.ok) {
    throw new Error(`Failed to close shift: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as MobileShiftData
}

export function useShift() {
  const token = useAuthStore((s) => s.accessToken)
  const query = useQuery({
    queryKey: ['shift', 'current'],
    queryFn: () => fetchShift(token),
    enabled: !!token,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })

  const openMutation = useMutation({ mutationFn: () => openShift(token) })
  const closeMutation = useMutation({ mutationFn: () => closeShift(token) })

  return {
    ...query,
    openShift: openMutation.mutateAsync,
    closeShift: closeMutation.mutateAsync,
  }
}
