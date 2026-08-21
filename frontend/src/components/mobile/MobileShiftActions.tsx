import { useState } from 'react'
import { useShift } from '@/hooks/useShift'

interface MobileShiftActionsProps {
  isOpen: boolean
}

export function MobileShiftActions({ isOpen }: MobileShiftActionsProps) {
  const { openShift, closeShift } = useShift()
  const [actionLoading, setActionLoading] = useState(false)

  const handleAction = async (action: 'open' | 'close') => {
    setActionLoading(true)
    try {
      if (action === 'open') {
        await openShift()
      } else {
        await closeShift()
      }
    } catch (error) {
      console.error(`Failed to ${action} shift:`, error)
      alert(`Failed to ${action} shift. Please try again.`)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4" data-testid="mobile-shift-actions" aria-labelledby="shift-actions-heading">
      <h2 id="shift-actions-heading" className="text-base font-semibold text-gray-900 mb-3">Actions</h2>
      <div className="flex gap-3">
        {isOpen ? (
          <button
            onClick={() => handleAction('close')}
            disabled={actionLoading}
            className="flex-1 bg-red-600 text-white py-3 rounded-lg font-medium touch-target-min disabled:opacity-50"
          >
            {actionLoading ? 'Closing...' : 'Close Shift'}
          </button>
        ) : (
          <button
            onClick={() => handleAction('open')}
            disabled={actionLoading}
            className="flex-1 bg-green-600 text-white py-3 rounded-lg font-medium touch-target-min disabled:opacity-50"
          >
            {actionLoading ? 'Opening...' : 'Open Shift'}
          </button>
        )}
      </div>
    </div>
  )
}
