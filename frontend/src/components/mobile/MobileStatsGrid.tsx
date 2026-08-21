import { formatPaise } from '@/hooks/useFormatPaise'

interface StatCardProps {
  label: string
  value: string | number
  testId: string
  icon?: React.ReactNode
}

export function StatCard({ label, value, testId, icon }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 touch-target-min" data-testid={testId}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-500 font-medium">{label}</span>
        {icon && <span className="text-xl">{icon}</span>}
      </div>
      <div className="text-2xl font-bold text-gray-900 tabular-nums">{value}</div>
    </div>
  )
}

export function MobileStatsGrid({ revenueToday, activeSessions, shiftSummary }: {
  revenueToday: number
  activeSessions: number
  shiftSummary: { revenue: number; sessions: number; avgDuration: number }
}) {
  return (
    <div className="grid grid-cols-2 gap-3 mb-6" data-testid="mobile-stats-grid" role="region" aria-label="Key metrics">
      <StatCard label="Today's Revenue" value={formatPaise(revenueToday)} testId="stat-revenue" icon="💰" />
      <StatCard label="Active Sessions" value={activeSessions} testId="stat-sessions" icon="🖥️" />
      <StatCard label="Shift Revenue" value={formatPaise(shiftSummary.revenue)} testId="stat-shift-revenue" icon="📊" />
      <StatCard label="Shift Sessions" value={shiftSummary.sessions} testId="stat-shift-sessions" icon="👥" />
    </div>
  )
}
