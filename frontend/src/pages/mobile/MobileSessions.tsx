import { useSessions } from '@/hooks/useSessions'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useState, useEffect } from 'react'
import { MobileSessionList } from '@/components/mobile/MobileSessionList'
import { MobileSessionDetailModal } from '@/components/mobile/MobileSessionDetailModal'
import { MobileZoneFilter } from '@/components/mobile/MobileZoneFilter'
import type { MobileSession } from '@/types/mobileAnalytics'

export function MobileSessions() {
  const { data: sessions, refetch } = useSessions()
  const { subscribe } = useWebSocket()
  const [selectedSession, setSelectedSession] = useState<MobileSession | null>(null)
  const [zoneFilter, setZoneFilter] = useState<string>('all')

  useEffect(() => {
    const unsubscribe = subscribe('sessions', () => refetch())
    return unsubscribe
  }, [subscribe, refetch])

  const filteredSessions = sessions?.filter(s => zoneFilter === 'all' || s.zoneName === zoneFilter) ?? []
  const zones = ['all', ...new Set(sessions?.map(s => s.zoneName) ?? [])]

  if (!sessions) {
    return (
      <div className="min-h-[400px] flex items-center justify-center" data-testid="mobile-sessions-loading">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div data-testid="mobile-sessions">
      <MobileZoneFilter zones={zones} value={zoneFilter} onChange={setZoneFilter} />
      <MobileSessionList sessions={filteredSessions} onSelect={setSelectedSession} />
      {selectedSession && (
        <MobileSessionDetailModal session={selectedSession} onClose={() => setSelectedSession(null)} />
      )}
    </div>
  )
}
