import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'

const API_BASE = '/api'

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export interface MobileSettings {
  cafeName: string
  timezone: string
  currency: string
  autoCloseShift: boolean
  sessionTimeout: number
  enableMembers: boolean
  enableTournaments: boolean
  printerEnabled: boolean
  printerIp: string
}

async function fetchSettings(token: string | null): Promise<MobileSettings> {
  const res = await fetch(`${API_BASE}/settings`, { headers: authHeaders(token) })
  if (!res.ok) {
    throw new Error(`Failed to load settings: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as MobileSettings
}

async function updateSettings(token: string | null, data: Partial<MobileSettings>): Promise<MobileSettings> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    throw new Error(`Failed to update settings: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as MobileSettings
}

export function useSettings() {
  const token = useAuthStore((s) => s.accessToken)
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['settings'],
    queryFn: () => fetchSettings(token),
    enabled: !!token,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  })

  const mutation = useMutation({
    mutationFn: (data: Partial<MobileSettings>) => updateSettings(token, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  return {
    ...query,
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
  }
}
