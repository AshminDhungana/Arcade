import { useAnalytics } from '@/hooks/useAnalytics'
import { useWebSocket } from '@/hooks/useWebSocket'
import { MobileStatsGrid } from '@/components/mobile/MobileStatsGrid'
import { MobileTopZones } from '@/components/mobile/MobileTopZones'
import { MobileActiveSessionsList } from '@/components/mobile/MobileActiveSessionsList'
import { useEffect } from 'react'

export function MobileDashboard() {
  const { data: analytics, refetch } = useAnalytics()
  const { subscribe } = useWebSocket()

  useEffect(() => {
    const unsubscribe = subscribe('analytics', () => refetch())
    return unsubscribe
  }, [subscribe, refetch])

  if (!analytics) {
    return (
      <div className="min-h-[400px] flex items-center justify-center" data-testid="mobile-dashboard-loading">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div data-testid="mobile-dashboard">
      <MobileStatsGrid
        revenueToday={analytics.revenueToday}
        activeSessions={analytics.activeSessions}
        shiftSummary={analytics.shiftSummary}
      />
      <MobileTopZones zones={analytics.topZones} />
      <MobileActiveSessionsList sessions={analytics.activeSessionsList} />
    </div>
  )
}
