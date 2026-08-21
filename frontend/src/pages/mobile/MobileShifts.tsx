import { useShift } from '@/hooks/useShift'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useEffect } from 'react'
import { MobileShiftStatus } from '@/components/mobile/MobileShiftStatus'
import { MobileShiftSummary } from '@/components/mobile/MobileShiftSummary'
import { MobileShiftActions } from '@/components/mobile/MobileShiftActions'

export function MobileShifts() {
  const { data: shiftData, refetch } = useShift()
  const { subscribe } = useWebSocket()

  useEffect(() => {
    const unsubscribe = subscribe('shifts', () => refetch())
    return unsubscribe
  }, [subscribe, refetch])

  if (!shiftData) {
    return (
      <div className="min-h-[400px] flex items-center justify-center" data-testid="mobile-shifts-loading">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div data-testid="mobile-shifts" className="space-y-4">
      <MobileShiftStatus isOpen={shiftData.isOpen} shift={shiftData.shift} />
      <MobileShiftSummary summary={shiftData.summary} />
      <MobileShiftActions isOpen={shiftData.isOpen} />
    </div>
  )
}
