import { formatPaise } from '@/hooks/useFormatPaise'

interface Zone {
  zoneId: string
  name: string
  revenue: number
  utilization: number
}

export function MobileTopZones({ zones }: { zones: Zone[] }) {
  return (
    <section className="bg-white rounded-lg border border-gray-200 overflow-hidden" data-testid="mobile-top-zones" aria-labelledby="top-zones-heading">
      <h2 id="top-zones-heading" className="px-4 py-3 text-base font-semibold text-gray-900 border-b border-gray-200">
        Top Zones
      </h2>
      <ul className="divide-y divide-gray-200" role="list">
        {zones.map((zone) => (
          <li key={zone.zoneId} className="px-4 py-3 flex items-center justify-between touch-target-min">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900 truncate">{zone.name}</span>
                <span className="text-xs text-gray-500 whitespace-nowrap">{Math.round(zone.utilization * 100)}% util</span>
              </div>
              <div className="mt-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-300"
                  style={{ width: `${zone.utilization * 100}%` }}
                  role="progressbar"
                  aria-valuenow={Math.round(zone.utilization * 100)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${zone.name} utilization`}
                />
              </div>
            </div>
            <div className="text-right ml-4">
              <div className="text-sm font-semibold text-gray-900 tabular-nums">{formatPaise(zone.revenue)}</div>
              <div className="text-xs text-gray-500">Revenue</div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
