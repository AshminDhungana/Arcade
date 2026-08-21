import { formatDuration } from '@/utils/formatDuration'

interface Session {
  id: string
  seatName: string
  zoneName: string
  memberName?: string
  startTime: string
  duration: number
  status: 'IN_USE' | 'PAUSED'
}

interface MobileSessionDetailModalProps {
  session: Session
  onClose: () => void
}

export function MobileSessionDetailModal({ session, onClose }: MobileSessionDetailModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/50" role="dialog" aria-modal="true" aria-labelledby="session-detail-title">
      <div className="bg-white rounded-t-2xl w-full max-h-[85vh] overflow-y-auto" data-testid="session-detail-modal">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <h2 id="session-detail-title" className="text-lg font-semibold text-gray-900">{session.seatName}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 touch-target-min p-1" aria-label="Close">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Zone</div>
              <div className="font-medium text-gray-900">{session.zoneName}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Status</div>
              <div className={`font-medium ${session.status === 'PAUSED' ? 'text-yellow-700' : 'text-green-700'}`}>
                {session.status}
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Member</div>
              <div className="font-medium text-gray-900">{session.memberName || 'Walk-in'}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Duration</div>
              <div className="font-medium text-gray-900 tabular-nums">{formatDuration(session.duration)}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 col-span-2">
              <div className="text-xs text-gray-500">Started</div>
              <div className="font-medium text-gray-900">{new Date(session.startTime).toLocaleString()}</div>
            </div>
          </div>

          <div className="flex gap-3 pt-2 border-t border-gray-200">
            <button className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-medium touch-target-min">
              Extend Session
            </button>
            <button className="flex-1 bg-red-600 text-white py-3 rounded-lg font-medium touch-target-min">
              End Session
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
