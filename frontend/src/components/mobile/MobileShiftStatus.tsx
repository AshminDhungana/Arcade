interface MobileShiftStatusProps {
  isOpen: boolean
  shift: { id: string; openedAt: string; openedBy: string } | null
}

export function MobileShiftStatus({ isOpen, shift }: MobileShiftStatusProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4" data-testid="mobile-shift-status" aria-labelledby="shift-status-heading">
      <h2 id="shift-status-heading" className="text-base font-semibold text-gray-900 mb-3">Shift Status</h2>
      <div className="flex items-center justify-between">
        <div>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${isOpen ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
            {isOpen ? 'Shift Open' : 'Shift Closed'}
          </span>
          {shift && isOpen && (
            <div className="mt-2 text-sm text-gray-500 space-y-1">
              <div>Opened by: <span className="text-gray-900 font-medium">{shift.openedBy}</span></div>
              <div>Started: <span className="text-gray-900 font-medium">{new Date(shift.openedAt).toLocaleString()}</span></div>
            </div>
          )}
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-gray-900 tabular-nums">{isOpen ? 'ACTIVE' : 'INACTIVE'}</div>
        </div>
      </div>
    </div>
  )
}
