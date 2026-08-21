import { formatPaise } from '@/hooks/useFormatPaise'

interface MobileShiftSummaryProps {
  summary: { revenue: number; sessions: number; avgDuration: number; posRevenue: number }
}

export function MobileShiftSummary({ summary }: MobileShiftSummaryProps) {
  return (
    <section className="bg-white rounded-lg border border-gray-200 overflow-hidden" data-testid="mobile-shift-summary" aria-labelledby="shift-summary-heading">
      <h2 id="shift-summary-heading" className="px-4 py-3 text-base font-semibold text-gray-900 border-b border-gray-200">
        Shift Summary
      </h2>
      <div className="grid grid-cols-2 gap-3 p-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs text-gray-500">Total Revenue</div>
          <div className="text-xl font-bold text-gray-900 tabular-nums">{formatPaise(summary.revenue)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs text-gray-500">POS Revenue</div>
          <div className="text-xl font-bold text-gray-900 tabular-nums">{formatPaise(summary.posRevenue)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs text-gray-500">Sessions</div>
          <div className="text-xl font-bold text-gray-900 tabular-nums">{summary.sessions}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="text-xs text-gray-500">Avg Duration</div>
          <div className="text-xl font-bold text-gray-900 tabular-nums">{Math.round(summary.avgDuration)}m</div>
        </div>
      </div>
    </section>
  )
}
