interface MobileZoneFilterProps {
  zones: string[]
  value: string
  onChange: (value: string) => void
}

export function MobileZoneFilter({ zones, value, onChange }: MobileZoneFilterProps) {
  return (
    <div className="mb-4" data-testid="mobile-zone-filter">
      <label htmlFor="zone-filter" className="sr-only">Filter by zone</label>
      <select
        id="zone-filter"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-base appearance-none bg-no-repeat bg-right pr-10 touch-target-min"
        style={{
          backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e\")",
          backgroundPosition: 'right 0.5rem center',
          backgroundSize: '1.5em 1.5em',
        }}
        role="combobox"
        aria-label="Filter sessions by zone"
      >
        {zones.map((zone) => (
          <option key={zone} value={zone}>
            {zone === 'all' ? 'All Zones' : zone}
          </option>
        ))}
      </select>
    </div>
  )
}
