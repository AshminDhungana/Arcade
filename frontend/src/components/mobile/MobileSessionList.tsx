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

interface MobileSessionListProps {
  sessions: Session[]
  onSelect: (session: Session) => void
}

export function MobileSessionList({ sessions, onSelect }: MobileSessionListProps) {
  if (sessions.length === 0) {
    return (
      <section className="bg-white rounded-lg border border-gray-200 p-6 text-center" data-testid="mobile-session-list">
        <p className="text-gray-500">No active sessions</p>
      </section>
    )
  }

  return (
    <section className="bg-white rounded-lg border border-gray-200 overflow-hidden" data-testid="mobile-session-list" aria-labelledby="sessions-heading">
      <h2 id="sessions-heading" className="px-4 py-3 text-base font-semibold text-gray-900 border-b border-gray-200">
        Active Sessions ({sessions.length})
      </h2>
      <ul className="divide-y divide-gray-200" role="list">
        {sessions.map((session) => (
          <li key={session.id} className="px-4 py-3 touch-target-min" onClick={() => onSelect(session)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onSelect(session)}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-gray-900 truncate">{session.seatName}</span>
                  <span className="text-xs text-gray-500 whitespace-nowrap">{session.zoneName}</span>
                  {session.memberName && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full whitespace-nowrap">{session.memberName}</span>
                  )}
                  <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${
                    session.status === 'PAUSED'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {session.status}
                  </span>
                </div>
                <div className="mt-1 text-sm text-gray-500">
                  Started {new Date(session.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} •
                  {' '}
                  {formatDuration(session.duration)}
                </div>
              </div>
              <span className="text-gray-400 text-xl flex-shrink-0">›</span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
